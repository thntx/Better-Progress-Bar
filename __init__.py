from aqt import mw
import aqt
from aqt.gui_hooks import reviewer_did_answer_card, state_did_change, sync_did_finish, reviewer_did_show_question
from aqt.qt import *
from .progressbar import ProgressBarWidget
import time

# Global instance
chunk_widget = None
card_widget = None

# State tracking
# History stores (current_count, status_log_list, time_log_list) snapshots
history = [] 
status_log = [] # True=Pass, False=Fail
time_log = [] # Float seconds
start_time = 0
current_count = 0
initial_total = None  # Original total at session start, for excess calculation

def on_show_question(card):
    global start_time
    start_time = time.time()

def on_answer(reviewer, card, ease):
    global chunk_widget, card_widget, status_log, time_log, start_time, current_count, initial_total
    
    config = mw.addonManager.getConfig(__name__)
    fail_policy = config.get("fail_policy", "ignore")
    timer_conf = config.get("timer", {})
    use_cap = timer_conf.get("use_anki_cap", True)
    
    passed = ease > 1
    
    # Calculate Time
    elapsed = 0
    if use_cap:
        # card.time_taken() returns ms
        elapsed = card.time_taken() / 1000.0
    else:
        now = time.time()
        if start_time > 0:
            elapsed = now - start_time
        else:
            elapsed = 0 # Fallback
            
    # Decide if we update state
    should_update = False
    
    is_pass = ease > 1
    
    should_update = False
    
    is_pass = ease > 1
    
    should_update = False
    
    if is_pass:
        should_update = True
        result = ease
    else:
        # Failed (ease 1)
        # Handle 'count' legacy as 'acknowledge'
        if fail_policy in ["acknowledge", "count"]:
            should_update = True
            result = ease
        else:
            should_update = False
            
    if should_update:
        # SNAPSHOT BEFORE CHANGE
        history.append((current_count, list(status_log), list(time_log)))
        
        # APPLY CHANGE
        current_count += 1
        status_log.append(result)
        time_log.append(elapsed)
        
    # Use a small delay to allow Anki's scheduler to update its counts
    QTimer.singleShot(50, refresh_bar)

def on_undo(action_name=None):
    global status_log, time_log, current_count
    if mw.state != "review":
        return
    
    config = mw.addonManager.getConfig(__name__)
    policy = config.get("undo_policy", "undo")

    if policy == "acknowledge":
        # Check if we have a log to mark
        if status_log:
            # Mark the last action as undone (grey out)
            status_log[-1] = "undone"
            
            if len(time_log) == len(status_log):
                time_log[-1] = 0
            # We do NOT pop history or revert 'current' count.
    else:
        # Standard Undo: Revert state
        if history:
            prev_current, prev_log, prev_time = history.pop()
            current_count = prev_current
            status_log = prev_log
            time_log = prev_time
    
    QTimer.singleShot(50, refresh_bar)

def reconstruct_history():
    global status_log, time_log, current_count, initial_total
    
    # Reset
    current_count = 0
    status_log = []
    time_log = []
    initial_total = None  # Will be set when we calculate the first total
    
    # Context
    did = mw.col.decks.selected()
    if not did: return
    
    # Get all cards in current deck tree
    try:
        valid_cids = set(mw.col.decks.cids(did, children=True))
    except:
        return 
    
    # Time boundaries
    cutoff_ms = (mw.col.sched.day_cutoff - 86400) * 1000
    
    # Query revlog
    entries = mw.col.db.all(f"select cid, ease, time from revlog where id > {cutoff_ms} order by id")
    
    config = mw.addonManager.getConfig(__name__)
    fail_policy = config.get("fail_policy", "ignore")
    
    for (cid, ease, time_ms) in entries:
        if cid not in valid_cids:
            continue
            
        is_fail = (ease == 1)
        elapsed = time_ms / 1000.0
        
        if fail_policy in ["acknowledge", "count"]:
            # Acknowledge mode: always advance, use actual ease
            status_log.append(ease) 
            time_log.append(elapsed)
            current_count += 1
        else:
            # Ignore mode: only advance on pass
            if not is_fail:
                status_log.append(ease)
                time_log.append(elapsed)
                current_count += 1

def on_state_change(new_state, old_state):
    # Show only in reviewer
    if new_state == "review":
        reconstruct_history()
        QTimer.singleShot(50, refresh_bar)
        if chunk_widget: chunk_widget.show()
        if card_widget: card_widget.show()
    elif new_state == "deckBrowser":
        if chunk_widget: chunk_widget.hide()
        if card_widget: card_widget.hide()
    elif new_state == "overview":
        if chunk_widget: chunk_widget.hide()
        if card_widget: card_widget.hide()

def on_sync_finished():
    if mw.state == "review":
        reconstruct_history()
        QTimer.singleShot(50, refresh_bar)

def refresh_bar():
    global initial_total
    
    if not mw.col:
        return
        
    counts = mw.col.sched.counts()
    config = mw.addonManager.getConfig(__name__)
    
    if config.get("double_new", True):
        remaining = (counts[0] * 2) + counts[1] + counts[2]
    else:
        remaining = sum(counts)
        
    total = current_count + remaining
    
    # Set initial_total on first call
    # For excess calculation, initial_total should be number of UNIQUE cards, not total reviews
    if initial_total is None:
        # Count failed cards in status_log (when fail_policy is acknowledge/count)
        fail_policy = config.get("fail_policy", "ignore")
        if fail_policy in ["acknowledge", "count"]:
            # Count fails (ease == 1 or False)
            num_fails = sum(1 for ease in status_log if ease == 1 or ease == False)
            # Initial total = current total - number of fails (since fails are re-reviews, not unique cards)
            initial_total = total - num_fails
        else:
            # No fail tracking, initial equals current
            initial_total = total
    
    if chunk_widget:
        chunk_widget.set_params(total, current_count, status_log, time_log, start_time, initial_total)
    if card_widget:
        card_widget.set_params(total, current_count, status_log, time_log, start_time, initial_total)

# Settings Menu
def open_settings():
    from .settings import SettingsDialog
    config = mw.addonManager.getConfig(__name__)
    # Ensure default structure if missing keys
    d = SettingsDialog(mw, config)
    if d.exec():
        # Config saved by dialog
        new_conf = mw.addonManager.getConfig(__name__)
        # Update widgets configs and layout
        if chunk_widget: chunk_widget.update_config(new_conf)
        if card_widget: card_widget.update_config(new_conf)
        apply_layout(new_conf)

def apply_layout(config):
    # Determine positions
    # default fallback
    d_area = config.get("dock_area", "top")
    positions = config.get("positions", {})
    chunk_pos = positions.get("chunks", d_area)
    card_pos = positions.get("cards", "bottom")
    
    # Remove existing
    if chunk_widget:
        chunk_widget.setParent(None)
        mw.mainLayout.removeWidget(chunk_widget)
        
    if card_widget:
        card_widget.setParent(None)
        mw.mainLayout.removeWidget(card_widget)
        
    # Re-insert
    # Order: Index 0 is Top. addWidget is Bottom.
    # If both Top: Insert Card first at 0, then Chunk at 0 -> Chunk is above Card.
    # User Request: "let users set ... sepparately".
    
    # Cards
    if card_pos == "top":
         mw.mainLayout.insertWidget(0, card_widget)
    elif card_pos == "bottom":
         mw.mainLayout.addWidget(card_widget)
         
    # Chunks (Inserted last at 0 will appear ABOVE cards if both are top)
    if chunk_pos == "top":
         mw.mainLayout.insertWidget(0, chunk_widget)
    elif chunk_pos == "bottom":
         mw.mainLayout.addWidget(chunk_widget)

    # Visibility handled by state logic via setParent? 
    # Calling setParent(None) effectively hides/removes.
    # We must ensure they are visible if in review state.
    if mw.state == "review":
        if chunk_pos != "hidden": chunk_widget.show()
        else: chunk_widget.hide()
        
        if card_pos != "hidden": card_widget.show()
        else: card_widget.hide()

# Initialization
def init_addon():
    global chunk_widget, card_widget
    
    chunk_widget = ProgressBarWidget("chunks")
    chunk_widget.settings_callback = open_settings
    
    card_widget = ProgressBarWidget("cards")
    card_widget.settings_callback = open_settings
    
    config = mw.addonManager.getConfig(__name__)
    chunk_widget.update_config(config)
    card_widget.update_config(config)
    
    # Link hover states so hovering over either bar triggers both
    chunk_widget.hover_callback = card_widget.set_hover_state
    card_widget.hover_callback = chunk_widget.set_hover_state
    
    apply_layout(config)
    
    # Start hidden
    chunk_widget.hide()
    card_widget.hide()

    # Hooks
    reviewer_did_answer_card.append(on_answer)
    reviewer_did_show_question.append(on_show_question)
    state_did_change.append(on_state_change)
    sync_did_finish.append(on_sync_finished)
    
    # Reliable Undo Hook
    if hasattr(aqt.gui_hooks, "state_did_undo"):
        aqt.gui_hooks.state_did_undo.append(on_undo)
    elif hasattr(aqt.gui_hooks, "reviewer_did_undo"):
        aqt.gui_hooks.reviewer_did_undo.append(on_undo)
    
    # Settings
    mw.addonManager.setConfigUpdatedAction(__name__, lambda c: open_settings()) # Logic implies global update, reusing generic

    # Add menu item
    action = QAction("Progress Bar Settings", mw)
    action.triggered.connect(open_settings)
    mw.form.menuTools.addAction(action)

init_addon()
