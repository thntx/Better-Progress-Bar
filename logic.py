from aqt import mw
from aqt.utils import tooltip
from aqt.qt import QTimer
import time
from .config_utils import DEFAULT_CONFIG, get_config_val
from .state import session
from . import layout
from . import fsrs_logic

def on_show_question(card):
    # CATCH-ALL: Check if previous card was skipped (Buried/Suspended) without triggering a hook
    if session.last_card_id and not session.was_answered and not session.last_action_handled:
        try:
            prev_card = mw.col.getCard(session.last_card_id)
            # Queue: -1=Suspended, -2=User Buried, -3=Sched Buried
            if prev_card.queue == -1:
                # Detected Missed Suspend
                _handle_other_event("suspend_policy", "suspended", prev_card)
            elif prev_card.queue in [-2, -3]:
                # Detected Missed Bury
                _handle_other_event("bury_policy", "buried", prev_card)
        except:
             pass # Card might be deleted or invalid
    
    # Reset for this card
    session.last_card_id = card.id
    session.was_answered = False
    session.last_action_handled = False
    session.start_time = time.time()

def on_answer(reviewer, card, ease):
    config = mw.addonManager.getConfig(__name__)
    fail_policy = get_config_val(config, DEFAULT_CONFIG, "fail_policy")
    use_cap = get_config_val(config, DEFAULT_CONFIG, "timer", "use_anki_cap")
    
    passed = ease > 1
    
    # Calculate Time
    elapsed = 0
    if use_cap:
        # card.time_taken() returns ms
        elapsed = card.time_taken() / 1000.0
    else:
        now = time.time()
        if session.start_time > 0:
            elapsed = now - session.start_time
        else:
            elapsed = 0 # Fallback
            
    # Decide if we update state
    should_update = False
    is_pass = ease > 1
    
    session.was_answered = True
    session.last_action_handled = True
    session.last_handled_card_id = card.id
    
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
        session.history.append((session.current_count, list(session.status_log), list(session.time_log)))
        
        # APPLY CHANGE
        session.current_count += 1
        session.status_log.append(result)
        session.time_log.append(elapsed)
        
    # Use a small delay to allow Anki's scheduler to update its counts
    QTimer.singleShot(50, refresh_bar)

def on_bury(reviewer, card):
    if session.last_action_handled:
        return
    if session.last_handled_card_id == card.id:
        return
    session.last_action_handled = True
    _handle_other_event("bury_policy", "buried", card)

def on_suspend(reviewer, card):
    if session.last_action_handled:
        return
    if session.last_handled_card_id == card.id:
        return
    session.last_action_handled = True
    _handle_other_event("suspend_policy", "suspended", card)

def _handle_other_event(policy_key, result_code, card):
    config = mw.addonManager.getConfig(__name__)
    policy = get_config_val(config, DEFAULT_CONFIG, policy_key)


    
    # tooltip(f"[Debug] Policy: {policy_key} = {policy}")
    
    # Calculate elapsed first (needed for manual action storage)
    elapsed = 0
    use_cap = get_config_val(config, DEFAULT_CONFIG, "timer", "use_anki_cap")
    if use_cap:
        try:
            elapsed = card.time_taken() / 1000.0
        except:
             elapsed = 0
    else:
        now = time.time()
        if session.start_time > 0:
            elapsed = now - session.start_time

    # STORE MANUAL ACTION
    if not hasattr(session, "manual_actions"):
        session.manual_actions = []
        
    current_did = mw.col.decks.selected()
        
    session.manual_actions.append({
        "cid": card.id,
        "did": current_did,
        "type": result_code, 
        "time": time.time(),
        "elapsed": elapsed
    })
    
    # Mark this card as effectively handled (prevent double counting)
    session.last_handled_card_id = card.id
    
    if policy == "acknowledge":
        # SNAPSHOT BEFORE CHANGE
        session.history.append((session.current_count, list(session.status_log), list(session.time_log)))

        
        # APPLY CHANGE
        session.current_count += 1
        session.status_log.append(result_code)
        session.time_log.append(elapsed)
        
        QTimer.singleShot(50, refresh_bar)


def on_undo(action_name=None):
    if mw.state != "review":
        return
    
    config = mw.addonManager.getConfig(__name__)
    policy = get_config_val(config, DEFAULT_CONFIG, "undo_policy")

    if policy == "acknowledge":
        # Check if we have a log to mark
        if session.status_log:
            # Mark the last action as undone (grey out)
            session.status_log[-1] = "undone"
            
            if len(session.time_log) == len(session.status_log):
                session.time_log[-1] = 0
            # We do NOT pop history or revert 'current' count.
    else:
        # Standard Undo: Revert state
        if session.history:
            prev_current, prev_log, prev_time = session.history.pop()
            session.current_count = prev_current
            session.status_log = prev_log
            session.time_log = prev_time
            
    # Reset last action handled so we can re-handle the same card if user retries
    session.last_handled_card_id = None
    session.last_action_handled = False
    
    QTimer.singleShot(50, refresh_bar)

def reconstruct_history():
    # Reset
    session.current_count = 0
    session.status_log = []
    session.time_log = []
    session.initial_total = None  # Will be set when we calculate the first total
    
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
    fail_policy = get_config_val(config, DEFAULT_CONFIG, "fail_policy")
    
    for (cid, ease, time_ms) in entries:
        if cid not in valid_cids:
            # log_debug(f"Skipping cid {cid} - not in current deck")
            continue

            
        is_fail = (ease == 1)
        elapsed = time_ms / 1000.0
        
        if fail_policy in ["acknowledge", "count"]:
            # Acknowledge mode: always advance, use actual ease
            session.status_log.append(ease) 
            session.time_log.append(elapsed)
            session.current_count += 1
        else:
            # Ignore mode: only advance on pass
            if not is_fail:
                session.status_log.append(ease)
                session.time_log.append(elapsed)
                session.current_count += 1

                


    # MERGE MANUAL ACTIONS
    # If recent manual actions are missing from DB (revlog), add them now.
    if hasattr(session, "manual_actions") and session.manual_actions:
        # Get IDs found in DB
        db_cids = set(x[0] for x in entries)
        
        # Filter manual actions that are relevant to current session/deck
        for action in session.manual_actions:
            cid = action["cid"]
            action_did = action.get("did")
            
            # If we have a stored DID, use it to verify session match
            # Otherwise fall back to valid_cids check (legacy/safeguard)
            if action_did is not None:
                if action_did != did:
                    continue
            elif cid not in valid_cids:
                # Fallback if did not missing (shouldn't happen with new code)
                continue
                
            # Check if this card appeared in DB results recently?
            # Revlog doesn't easily map back to "this specific action" without timestamp match.
            # But "buried" usually doesn't create duplicate logs quickly.
            # If the card is NOT in the DB entries we just fetched (for today), we assume it's missing.
            # OR if it IS in DB, we assume DB covered it?
            # Issue: User might review card (DB OK) then Bury it (DB Missing).
            # So simple existence of CID in revlog isn't enough.
            # We need to know if the LATEST action is there.
            
            # Simple heuristic: If the action time is > last DB entry time for this CID?
            # Or just append if not found?
            
            # Use strict timestamp check?
            # Action time is seconds. Revlog is ms.
            action_ts_ms = action["time"] * 1000
            
            # Did we find an entry for this CID with similar timestamp?
            # allowed skew: 2 seconds
            found_in_db = False
            for (dcid, dease, dtime) in entries:
                if dcid == cid:
                    if abs(dtime - action_ts_ms) < 5000: # 5 seconds window
                         found_in_db = True
                         break
            
            if not found_in_db:
                session.status_log.append(action['type'])
                session.time_log.append(action['elapsed'])
                session.current_count += 1




def on_state_change(new_state, old_state):
    # FSRS Per-Deck Hook (running on overview/review entry)
    # MUST run before reconstruct_history to ensure correct weights/intervals
    if new_state in ["overview", "review"]:
        fsrs_logic.check_fsrs_deck_update()

    # Show only in reviewer
    if new_state == "review":
        # RESET TRACKING for fresh start
        session.last_card_id = None
        session.last_action_handled = False
        session.was_answered = False
        session.last_handled_card_id = None
        
        reconstruct_history()
        QTimer.singleShot(50, refresh_bar)
        if layout.chunk_widget: 
            layout.chunk_widget.show()
            layout.chunk_widget.update()
        if layout.card_widget: 
            layout.card_widget.show()
            layout.card_widget.update()
    elif new_state == "overview":
        if layout.chunk_widget: layout.chunk_widget.hide()
        if layout.card_widget: layout.card_widget.hide()

def on_sync_finished():
    if mw.state == "review":
        reconstruct_history()
        QTimer.singleShot(50, refresh_bar)

def refresh_bar():
    if not mw.col:
        return
        
    counts = mw.col.sched.counts()
    config = mw.addonManager.getConfig(__name__)
    
    if get_config_val(config, DEFAULT_CONFIG, "double_new"):
        remaining = (counts[0] * 2) + counts[1] + counts[2]
    else:
        remaining = sum(counts)
        
    total = session.current_count + remaining
    
    # Set initial_total on first call
    # For excess calculation, initial_total should be number of UNIQUE cards, not total reviews
    if session.initial_total is None:
        # Count failed cards in status_log (when fail_policy is acknowledge/count)
        fail_policy = get_config_val(config, DEFAULT_CONFIG, "fail_policy")
        if fail_policy in ["acknowledge", "count"]:
            # Count fails (ease == 1 or False)
            num_fails = sum(1 for ease in session.status_log if ease == 1 or ease == False)
            # Initial total = current total - number of fails (since fails are re-reviews, not unique cards)
            session.initial_total = total - num_fails
        else:
            # No fail tracking, initial equals current
            session.initial_total = total
    
    layout.refresh_widgets(total, session.current_count, session.status_log, session.time_log, session.start_time, session.initial_total)



