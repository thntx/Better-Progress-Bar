from aqt.qt import *
from aqt import mw

import json
import os

class SettingsDialog(QDialog):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.colors = {} # For global colors
        self.style_widgets = {} # For text options strings
        self.setWindowTitle("Progress Bar Settings")
        
        # Load defaults from config.json directly
        self.default_config = self._load_defaults()
        
        self.setup_ui()

    def _load_defaults(self):
        # Read the actual config.json file from disk, ignoring user's meta.json
        addon_dir = os.path.dirname(__file__)
        config_path = os.path.join(addon_dir, "config.json")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {} # Fallback or error? Preferably crash/log if missing.

    def setup_ui(self):
        main_layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # =======================
        # Tab 1: Style
        # =======================
        style_widget = QWidget()
        style_layout = QVBoxLayout()
        
        # --- Layout (Positions) ---
        layout_group = QGroupBox("Layout")
        layout_grid = QGridLayout()
        
        layout_grid.addWidget(QLabel("Chunk Bar:"), 0, 0)
        self.chunk_pos_combo = QComboBox()
        self.chunk_pos_combo.addItems(["top", "bottom", "hidden"])
        # Fallback to dock_area if positions missing
        def_pos = self.default_config.get("dock_area", "top")
        cur_pos = self.config.get("positions", {}).get("chunks", def_pos)
        self.chunk_pos_combo.setCurrentText(cur_pos)
        layout_grid.addWidget(self.chunk_pos_combo, 0, 1)
        
        layout_grid.addWidget(QLabel("Card Bar:"), 1, 0)
        self.card_pos_combo = QComboBox()
        self.card_pos_combo.addItems(["top", "bottom", "hidden"])
        cur_pos_c = self.config.get("positions", {}).get("cards", "bottom") # Default card bottom if split
        self.card_pos_combo.setCurrentText(cur_pos_c)
        layout_grid.addWidget(self.card_pos_combo, 1, 1)
        
        layout_group.setLayout(layout_grid)
        style_layout.addWidget(layout_group)
 
        # --- Text Options Helper ---
        text_opts = self.config.get("text_options", self.default_config.get("text_options", {}))
        top_opts = text_opts.get("top", {})
        bot_opts = text_opts.get("bottom", {})
        
        default_style = {"color": "#ffffff", "bold": True, "outline": True, "outline_color": "#303030"}
        
        # --- Chunk Bar Text ---
        top_group = QGroupBox("Chunk Bar Text")
        top_layout = QVBoxLayout()
        
        # Numbers
        n_conf = top_opts.get("numbers", {})
        self.top_num_widgets = self.add_text_section(top_layout, "Numbers", n_conf, default_style)
        
        # Percentages
        p_conf = top_opts.get("percentages", {})
        self.top_pct_widgets = self.add_text_section(top_layout, "Percentages", p_conf, default_style)
        
        top_group.setLayout(top_layout)
        style_layout.addWidget(top_group)
        
        # --- Card Bar Text ---
        bot_group = QGroupBox("Card Bar Text")
        bot_layout = QVBoxLayout()
        
        # Numbers
        n_conf_b = bot_opts.get("numbers", {})
        self.bot_num_widgets = self.add_text_section(bot_layout, "Numbers", n_conf_b, default_style)
        
        # Percentages
        p_conf_b = bot_opts.get("percentages", {})
        self.bot_pct_widgets = self.add_text_section(bot_layout, "Percentages", p_conf_b, default_style)
        
        bot_group.setLayout(bot_layout)
        style_layout.addWidget(bot_group)
        
        vis_opts = self.config.get("visual_options", {})
        self.auto_hide_cb = QCheckBox("Remove text when stretched (too small)")
        self.auto_hide_cb.setToolTip("Hides text if it doesn't fit within the tile.")
        self.auto_hide_cb.setChecked(vis_opts.get("auto_hide_text", False))
        style_layout.addWidget(self.auto_hide_cb)
        
        style_layout.addStretch()
        style_widget.setLayout(style_layout)
        self.tabs.addTab(style_widget, "Style")

        # =======================
        # Tab 2: Colors
        # =======================
        colors_tab = QWidget()
        colors_tab_layout = QVBoxLayout()

        # --- Base Colors ---
        color_group = QGroupBox("Base Colors")
        color_layout = QGridLayout()
        
        self.color_btns = {} 
        def_colors = self.default_config.get("colors", {})
        user_colors = self.config.get("colors", {})
        
        self.current_color_btn = self.create_color_btn(user_colors.get("current_chunk", def_colors.get("current_chunk")), "current_chunk")
        self.future_color_btn = self.create_color_btn(user_colors.get("future", def_colors.get("future")), "future")
        self.good_color_btn = self.create_color_btn(user_colors.get("good", def_colors.get("good", "#66cc66")), "good")
        self.hard_color_btn = self.create_color_btn(user_colors.get("hard", def_colors.get("hard", "#EEDD88")), "hard")
        self.easy_color_btn = self.create_color_btn(user_colors.get("easy", def_colors.get("easy", "#AA88DD")), "easy")
        self.again_color_btn = self.create_color_btn(user_colors.get("again", def_colors.get("again", user_colors.get("fail"))), "again")
        self.undo_color_btn = self.create_color_btn(user_colors.get("undo", def_colors.get("undo")), "undo")
        self.again_chunk_btn = self.create_color_btn(user_colors.get("again_chunk", def_colors.get("again_chunk", user_colors.get("fail_chunk"))), "again_chunk")
        
        color_layout.addWidget(QLabel("Current:"), 0, 0)
        color_layout.addWidget(self.current_color_btn, 0, 1)
        color_layout.addWidget(QLabel("Pending:"), 1, 0)
        color_layout.addWidget(self.future_color_btn, 1, 1)        
        color_layout.addWidget(QLabel("Good:"), 2, 0)
        color_layout.addWidget(self.good_color_btn, 2, 1)
        
        self.use_good_as_pass_cb = QCheckBox("Use for all pass")
        self.use_good_as_pass_cb.setToolTip("Uses the 'Good' color for Hard and Easy cards in the progress bar.")
        self.use_good_as_pass_cb.setChecked(vis_opts.get("use_good_for_all_pass", False))
        color_layout.addWidget(self.use_good_as_pass_cb, 2, 2)

        self.hard_label = QLabel("Hard:")
        color_layout.addWidget(self.hard_label, 3, 0)
        color_layout.addWidget(self.hard_color_btn, 3, 1)
        self.easy_label = QLabel("Easy:")
        color_layout.addWidget(self.easy_label, 4, 0)
        color_layout.addWidget(self.easy_color_btn, 4, 1)
        
        color_layout.addWidget(QLabel("Again:"), 5, 0)
        color_layout.addWidget(self.again_color_btn, 5, 1)
        color_layout.addWidget(QLabel("Undone:"), 6, 0)
        color_layout.addWidget(self.undo_color_btn, 6, 1)        
        
        self.excess_label = QLabel("Excess Chunk:")
        color_layout.addWidget(self.excess_label, 7, 0)
        color_layout.addWidget(self.again_chunk_btn, 7, 1)
        
        self.highlight_excess_cb = QCheckBox("Enable highlight")
        self.highlight_excess_cb.setToolTip("Highlights chunks that contain cards beyond the original total.")
        self.highlight_excess_cb.setChecked(vis_opts.get("highlight_excess", True))
        color_layout.addWidget(self.highlight_excess_cb, 7, 2)
        
        # Behavior Dependencies
        def update_pass_deps(checked):
            self.hard_color_btn.setEnabled(not checked)
            self.hard_label.setEnabled(not checked)
            self.easy_color_btn.setEnabled(not checked)
            self.easy_label.setEnabled(not checked)
        self.use_good_as_pass_cb.toggled.connect(update_pass_deps)
        update_pass_deps(self.use_good_as_pass_cb.isChecked())
        
        def update_excess_deps(checked):
            self.again_chunk_btn.setEnabled(checked)
            self.excess_label.setEnabled(checked)
        self.highlight_excess_cb.toggled.connect(update_excess_deps)
        update_excess_deps(self.highlight_excess_cb.isChecked())
        
        color_group.setLayout(color_layout)
        colors_tab_layout.addWidget(color_group)

        # --- Completed Chunk Coloring ---
        comp_group = QGroupBox("Completed Chunk Coloring")
        comp_layout = QVBoxLayout()

        self.only_pass_fail_cb = QCheckBox("Only use Pass/Fail colors")
        self.only_pass_fail_cb.setChecked(vis_opts.get("only_pass_fail", False))
        comp_layout.addWidget(self.only_pass_fail_cb)

        # Threshold UI
        threshold_w = QWidget()
        threshold_l = QHBoxLayout()
        threshold_l.setContentsMargins(20, 0, 0, 0)
        threshold_l.addWidget(QLabel("Failing"))
        
        self.fail_op_cb = QComboBox()
        self.fail_op_cb.addItems([">", ">="])
        self.fail_op_cb.setCurrentText(">" if vis_opts.get("fail_threshold_op", "gt") == "gt" else ">=")
        threshold_l.addWidget(self.fail_op_cb)
        
        self.fail_val_spin = QSpinBox()
        self.fail_val_spin.setRange(0, 9999)
        self.fail_val_spin.setValue(vis_opts.get("fail_threshold_val", 50))
        threshold_l.addWidget(self.fail_val_spin)
        
        self.fail_unit_cb = QComboBox()
        self.fail_unit_cb.addItems(["cards", "%"])
        self.fail_unit_cb.setCurrentText(vis_opts.get("fail_threshold_unit", "%"))
        threshold_l.addWidget(self.fail_unit_cb)
        
        threshold_l.addWidget(QLabel("will fail the chunk"))
        threshold_l.addStretch()
        threshold_w.setLayout(threshold_l)
        comp_layout.addWidget(threshold_w)

        self.fail_exact_striped_cb = QCheckBox("Failing exactly that number will set a stripped pattern")
        self.fail_exact_striped_cb.setChecked(vis_opts.get("fail_exact_striped", True))
        comp_layout.addWidget(self.fail_exact_striped_cb)

        def update_comp_deps(checked):
            threshold_w.setEnabled(checked)
            self.fail_exact_striped_cb.setEnabled(checked)
        self.only_pass_fail_cb.toggled.connect(update_comp_deps)
        update_comp_deps(self.only_pass_fail_cb.isChecked())

        comp_group.setLayout(comp_layout)
        colors_tab_layout.addWidget(comp_group)

        # --- Perfect Chunks ---
        perfect_group = QGroupBox("Perfect Chunks")
        perfect_layout = QHBoxLayout()
        self.highlight_perfect_cb = QCheckBox("Highlight perfect chunks")
        self.highlight_perfect_cb.setChecked(vis_opts.get("highlight_perfect", False))
        perfect_layout.addWidget(self.highlight_perfect_cb)
        
        self.perfect_include_hard_cb = QCheckBox("Include hard cards")
        self.perfect_include_hard_cb.setToolTip("Treat Hard cards as non-perfect (must be all Good/Easy).")
        self.perfect_include_hard_cb.setChecked(vis_opts.get("perfect_include_hard", True))
        perfect_layout.addWidget(self.perfect_include_hard_cb)
        
        self.perfect_color_btn = self.create_color_btn(user_colors.get("perfect_color", vis_opts.get("perfect_color", "#FFD700")), "perfect_color")
        perfect_layout.addWidget(self.perfect_color_btn)
        
        def update_perfect_deps(checked):
            self.perfect_include_hard_cb.setEnabled(checked)
            self.perfect_color_btn.setEnabled(checked)
        self.highlight_perfect_cb.toggled.connect(update_perfect_deps)
        update_perfect_deps(self.highlight_perfect_cb.isChecked())
        
        perfect_group.setLayout(perfect_layout)
        colors_tab_layout.addWidget(perfect_group)

        colors_tab_layout.addStretch()
        colors_tab.setLayout(colors_tab_layout)
        self.tabs.insertTab(1, colors_tab, "Colors")
 
        # =======================
        # Tab 2: Behaviour
        # =======================
        behavior_widget = QWidget()
        behavior_layout = QVBoxLayout()
        
        # Chunk Size
        h = QHBoxLayout()
        h.addWidget(QLabel("Chunk Size:"))
        self.chunk_spin = QSpinBox()
        self.chunk_spin.setRange(1, 100)
        self.chunk_spin.setValue(self.config.get("chunk_size", self.default_config.get("chunk_size", 10)))
        h.addWidget(self.chunk_spin)
        behavior_layout.addLayout(h)
 
        # Double New Option
        self.double_new_cb = QCheckBox("Assume new cards are reviewed twice")
        self.double_new_cb.setChecked(self.config.get("double_new", self.default_config.get("double_new", True)))
        behavior_layout.addWidget(self.double_new_cb)
        
        # --- Fail Policy ---
        policy_group = QGroupBox("Fail Policy")
        policy_layout = QFormLayout()
        
        self.fail_policy_cb = QComboBox()
        self.fail_policy_cb.addItems(["ignore", "acknowledge"])
        self.fail_policy_cb.setCurrentText(self.config.get("fail_policy", self.default_config.get("fail_policy", "acknowledge")))
        
        policy_layout.addRow("Action on Again:", self.fail_policy_cb)
        policy_group.setLayout(policy_layout)
        behavior_layout.addWidget(policy_group)
 
        # --- Undo Policy ---
        undo_group = QGroupBox("Undo Policy")
        undo_layout = QFormLayout()
        
        self.undo_policy_cb = QComboBox()
        self.undo_policy_cb.addItems(["undo", "acknowledge"])
        self.undo_policy_cb.setCurrentText(self.config.get("undo_policy", self.default_config.get("undo_policy", "undo")))
        
        undo_layout.addRow("Action on Undo:", self.undo_policy_cb)
        undo_group.setLayout(undo_layout)
        behavior_layout.addWidget(undo_group)
 
        behavior_layout.addStretch()
        behavior_widget.setLayout(behavior_layout)
        self.tabs.addTab(behavior_widget, "Behaviour")

        # =======================
        # Tab 3: Timer
        # =======================
        timer_widget = QWidget()
        timer_layout = QVBoxLayout()
        
        t_conf = self.config.get("timer", self.default_config.get("timer", {}))
        
        # --- General ---
        self.timer_cap = QCheckBox("Use Anki's max answer time (cap)")
        self.timer_cap.setChecked(t_conf.get("use_anki_cap", True))
        timer_layout.addWidget(self.timer_cap)
        
        # --- Chunk Timer ---
        chunk_g = QGroupBox("Chunk Timer")
        chunk_l = QVBoxLayout()
        chunk_conf = t_conf.get("chunk_timer", {})
        self.chunk_timer_widgets = self.add_timer_section(chunk_l, "Enable on Chunks", chunk_conf, default_style)
        chunk_g.setLayout(chunk_l)
        timer_layout.addWidget(chunk_g)
 
        # --- Card Timer ---
        card_g = QGroupBox("Card Timer")
        card_l = QVBoxLayout()
        card_conf = t_conf.get("card_timer", {})
        self.card_timer_widgets = self.add_timer_section(card_l, "Enable on Cards", card_conf, default_style)
        card_g.setLayout(card_l)
        timer_layout.addWidget(card_g)
        
        timer_layout.addStretch()
        timer_widget.setLayout(timer_layout)
        self.tabs.addTab(timer_widget, "Timer")
        
        # --- Main Buttons ---
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        restore_btn = btns.addButton("Restore Defaults", QDialogButtonBox.ButtonRole.ResetRole)
        restore_btn.clicked.connect(self.restore_defaults)
        
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        main_layout.addWidget(btns)
        
        self.setLayout(main_layout)

    # ... (Helpers like add_text_section are assumed here, skipped for brevity in tool call, but required in file) ...
    # Wait, replace_file_content must be exact. I am replacing from 56 (start setup_ui)?
    # No, I am replacing from definition of DEFAULT_CONFIG (line 4) through end of INIT?
    # This is a large chunk.
    # User's request is to REMOVE DEFAULT_CONFIG.
    # It starts at line 4, ends at 47.
    # Class SettingsDialog starts at 49.
    # I should replace lines 4-240 (covering init and setup_ui and imports).
    # I need to be careful not to delete helpers unless I include them.
    # I will replace lines 4 to 240 (roughly setup_ui end) with the new logic.



    def add_text_section(self, parent_layout, label_text, config_dict, default_style):
        # Create a horizontal row for the main options
        h = QHBoxLayout()
        
        # Checkbox
        enabled_cb = QCheckBox(label_text)
        enabled_cb.setChecked(config_dict.get("enabled", True))
        h.addWidget(enabled_cb)
        
        # Type
        type_combo = QComboBox()
        type_combo.addItems(["relative", "absolute", "total"])
        type_combo.setCurrentText(config_dict.get("type", "relative"))
        h.addWidget(type_combo)
        
        # Direction
        dir_combo = QComboBox()
        dir_combo.addItems(["done", "remaining"])
        dir_combo.setCurrentText(config_dict.get("count_direction", "done"))
        h.addWidget(dir_combo)
        
        parent_layout.addLayout(h)
        
        # Style Row
        h_style = QHBoxLayout()
        h_style.setContentsMargins(20, 0, 0, 5) # Indent
        
        h_style.addWidget(QLabel("Style:"))
        
        # Color
        cur_style = config_dict.get("style", default_style)
        
        color_btn = QPushButton()
        c_val = cur_style.get("color", "#ffffff")
        color_btn.setStyleSheet(f"background-color: {c_val}")
        color_btn.setProperty("hex_color", c_val)
        color_btn.clicked.connect(lambda: self.pick_style_color(color_btn))
        h_style.addWidget(color_btn)
        
        # Bold
        bold_cb = QCheckBox("Bold")
        bold_cb.setChecked(cur_style.get("bold", True))
        h_style.addWidget(bold_cb)
        
        # Outline
        outline_cb = QCheckBox("Outline")
        outline_cb.setChecked(cur_style.get("outline", False))
        h_style.addWidget(outline_cb)
        
        # Outline Color
        oc_val = cur_style.get("outline_color", "#000000")
        outline_btn = QPushButton()
        outline_btn.setStyleSheet(f"background-color: {oc_val}")
        outline_btn.setProperty("hex_color", oc_val)
        outline_btn.clicked.connect(lambda: self.pick_style_color(outline_btn))
        h_style.addWidget(outline_btn)
        
        parent_layout.addLayout(h_style)
        
        return {
            "enabled": enabled_cb,
            "type": type_combo,
            "dir": dir_combo,
            "color": color_btn,
            "bold": bold_cb,
            "outline": outline_cb,
            "outline_color": outline_btn
        }

    def add_timer_section(self, parent_layout, label_text, config_dict, default_style):
        # Main Enable + Live Row
        h = QHBoxLayout()
        enabled_cb = QCheckBox(label_text)
        enabled_cb.setChecked(config_dict.get("enabled", False))
        h.addWidget(enabled_cb)
        
        h.addSpacing(20)
        
        live_cb = QCheckBox("Show Live Timer")
        live_cb.setChecked(config_dict.get("live_enabled", False))
        h.addWidget(live_cb)
        
        h.addStretch()
        parent_layout.addLayout(h)
        
        # Format Row
        h_fmt = QHBoxLayout()
        h_fmt.setContentsMargins(20, 0, 0, 0)
        h_fmt.addWidget(QLabel("Format:"))
        
        fmt = config_dict.get("format", {})
        
        min_cb = QCheckBox("Minutes")
        min_cb.setChecked(fmt.get("minutes", False))
        h_fmt.addWidget(min_cb)
        
        sec_cb = QCheckBox("Seconds")
        sec_cb.setChecked(fmt.get("seconds", True))
        h_fmt.addWidget(sec_cb)
        
        ms_cb = QCheckBox("Milliseconds")
        ms_cb.setChecked(fmt.get("milliseconds", False))
        h_fmt.addWidget(ms_cb)
        
        # Logic: ms enabled only if sec enabled
        ms_cb.setEnabled(sec_cb.isChecked())
        def on_sec_change(checked):
            ms_cb.setEnabled(checked)
            if not checked: ms_cb.setChecked(False)
        sec_cb.toggled.connect(on_sec_change)

        h_fmt.addStretch()
        parent_layout.addLayout(h_fmt)
        
        # Style Row
        h_style = QHBoxLayout()
        h_style.setContentsMargins(20, 0, 0, 5)
        h_style.addWidget(QLabel("Style:"))
        
        cur_style = config_dict.get("style", default_style)
        
        color_btn = QPushButton()
        c_val = cur_style.get("color", "#ffffff")
        color_btn.setStyleSheet(f"background-color: {c_val}")
        color_btn.setProperty("hex_color", c_val)
        color_btn.clicked.connect(lambda: self.pick_style_color(color_btn))
        h_style.addWidget(color_btn)
        
        bold_cb = QCheckBox("Bold")
        bold_cb.setChecked(cur_style.get("bold", True))
        h_style.addWidget(bold_cb)
        
        # Outline
        outline_cb = QCheckBox("Outline")
        outline_cb.setChecked(cur_style.get("outline", False))
        h_style.addWidget(outline_cb)
        
        # Outline Color
        oc_val = cur_style.get("outline_color", "#000000")
        outline_btn = QPushButton()
        outline_btn.setStyleSheet(f"background-color: {oc_val}")
        outline_btn.setProperty("hex_color", oc_val)
        outline_btn.clicked.connect(lambda: self.pick_style_color(outline_btn))
        h_style.addWidget(outline_btn)
        
        h_style.addStretch()
        parent_layout.addLayout(h_style)
        
        return {
            "enabled": enabled_cb,
            "live": live_cb,
            "minutes": min_cb,
            "seconds": sec_cb,
            "milliseconds": ms_cb,
            "color": color_btn,
            "bold": bold_cb,
            "outline": outline_cb,
            "outline_color": outline_btn
        }

    def create_color_btn(self, color_str, key):
        btn = QPushButton()
        btn.setText(color_str)
        btn.setStyleSheet(f"background-color: {color_str}")
        self.colors[key] = color_str
        self.color_btns[key] = btn # Store for reset
        btn.clicked.connect(lambda _, k=key, b=btn: self.pick_color(k, b))
        return btn

    def pick_color(self, key, btn):
        curr = QColor(self.colors[key])
        color = QColorDialog.getColor(curr, self)
        if color.isValid():
            hex_c = color.name()
            self.colors[key] = hex_c
            btn.setText(hex_c)
            btn.setStyleSheet(f"background-color: {hex_c}")
            
    def pick_style_color(self, btn):
        curr = QColor(btn.property("hex_color"))
        color = QColorDialog.getColor(curr, self)
        if color.isValid():
            hex_c = color.name()
            btn.setProperty("hex_color", hex_c)
            btn.setStyleSheet(f"background-color: {hex_c}")

    def restore_defaults(self):
        # Confirm
        if QMessageBox.question(self, "Restore Defaults", "Are you sure you want to restore all settings to default?",
                                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return

        # Basic
        self.chunk_spin.setValue(self.default_config.get("chunk_size", 10))
        self.double_new_cb.setChecked(self.default_config.get("double_new", True))
        
        # Positions
        def_pos = self.default_config.get("positions", {})
        self.chunk_pos_combo.setCurrentText(def_pos.get("chunks", "top"))
        self.card_pos_combo.setCurrentText(def_pos.get("cards", "bottom"))
        
        # Visual Options
        vis_opts = self.default_config.get("visual_options", {})
        self.highlight_excess_cb.setChecked(vis_opts.get("highlight_excess", True))
        self.auto_hide_cb.setChecked(vis_opts.get("auto_hide_text", False))
        self.use_good_as_pass_cb.setChecked(vis_opts.get("use_good_for_all_pass", False))
        
        self.only_pass_fail_cb.setChecked(vis_opts.get("only_pass_fail", False))
        op_f = vis_opts.get("fail_threshold_op", "gt")
        self.fail_op_cb.setCurrentIndex(0 if op_f == "gt" else 1)
        self.fail_unit_cb.setCurrentText(vis_opts.get("fail_threshold_unit", "%"))
        self.fail_val_spin.setValue(vis_opts.get("fail_threshold_val", 50))
        self.fail_exact_striped_cb.setChecked(vis_opts.get("fail_exact_striped", True))
        
        self.highlight_perfect_cb.setChecked(vis_opts.get("highlight_perfect", False))
        self.perfect_include_hard_cb.setChecked(vis_opts.get("perfect_include_hard", True))
        self.auto_hide_cb.setChecked(vis_opts.get("auto_hide_text", False))
        
        self.fail_policy_cb.setCurrentText(self.default_config.get("fail_policy", "acknowledge"))
        self.undo_policy_cb.setCurrentText(self.default_config.get("undo_policy", "undo"))
        
        # Colors
        def_colors = self.default_config.get("colors", {})
        for k, v in def_colors.items():
            self.colors[k] = v
            btn = self.color_btns.get(k)
            if btn:
                btn.setText(v)
                btn.setStyleSheet(f"background-color: {v}")
                
        # Text Options
        def_txt = self.default_config.get("text_options", {})
        top_c = def_txt.get("top", {})
        bot_c = def_txt.get("bottom", {})
        
        def restore_section(widgets, conf):
            widgets["enabled"].setChecked(conf.get("enabled", True))
            widgets["type"].setCurrentText(conf.get("type", "relative"))
            widgets["dir"].setCurrentText(conf.get("count_direction", "done"))
            style = conf.get("style", {})
            widgets["color"].setProperty("hex_color", style.get("color", "#ffffff"))
            widgets["color"].setStyleSheet(f"background-color: {style.get('color', '#ffffff')}")
            widgets["bold"].setChecked(style.get("bold", True))
            widgets["outline"].setChecked(style.get("outline", False))
            widgets["outline_color"].setProperty("hex_color", style.get("outline_color", "#000000"))
            widgets["outline_color"].setStyleSheet(f"background-color: {style.get('outline_color', '#000000')}")

        restore_section(self.top_num_widgets, top_c.get("numbers", {}))
        restore_section(self.top_pct_widgets, top_c.get("percentages", {}))
        restore_section(self.bot_num_widgets, bot_c.get("numbers", {}))
        restore_section(self.bot_pct_widgets, bot_c.get("percentages", {}))
        
        # Timer
        dt = self.default_config.get("timer", {})
        self.timer_cap.setChecked(dt.get("use_anki_cap", True))
        
        def restore_timer_section(widgets, conf):
            widgets["enabled"].setChecked(conf.get("enabled", False))
            widgets["live"].setChecked(conf.get("live_enabled", False))
            fmt = conf.get("format", {})
            widgets["minutes"].setChecked(fmt.get("minutes", False))
            widgets["seconds"].setChecked(fmt.get("seconds", True))
            widgets["milliseconds"].setChecked(fmt.get("milliseconds", False))
            
            style = conf.get("style", {})
            widgets["color"].setProperty("hex_color", style.get("color", "#ffffff"))
            widgets["color"].setStyleSheet(f"background-color: {style.get('color', '#ffffff')}")
            widgets["bold"].setChecked(style.get("bold", True))
            widgets["outline"].setChecked(style.get("outline", False))
            widgets["outline_color"].setProperty("hex_color", style.get("outline_color", "#000000"))
            widgets["outline_color"].setStyleSheet(f"background-color: {style.get('outline_color', '#000000')}")

        restore_timer_section(self.chunk_timer_widgets, dt.get("chunk_timer", {}))
        restore_timer_section(self.card_timer_widgets, dt.get("card_timer", {}))

    def accept(self):
        # Save config
        self.config["chunk_size"] = self.chunk_spin.value()
        self.config["double_new"] = self.double_new_cb.isChecked()
        # Save positions
        self.config["positions"] = {
            "chunks": self.chunk_pos_combo.currentText(),
            "cards": self.card_pos_combo.currentText()
        }
        if "dock_area" in self.config:
            del self.config["dock_area"]
            
        self.config["fail_policy"] = self.fail_policy_cb.currentText()
        self.config["undo_policy"] = self.undo_policy_cb.currentText()
        self.config["colors"] = self.colors
        
        # Save Visual Options
        self.config["visual_options"] = {
            "highlight_excess": self.highlight_excess_cb.isChecked(),
            "auto_hide_text": self.auto_hide_cb.isChecked(),
            "use_good_for_all_pass": self.use_good_as_pass_cb.isChecked(),
            "only_pass_fail": self.only_pass_fail_cb.isChecked(),
            "fail_threshold_op": "gt" if self.fail_op_cb.currentIndex() == 0 else "ge",
            "fail_threshold_val": self.fail_val_spin.value(),
            "fail_threshold_unit": self.fail_unit_cb.currentText(),
            "fail_exact_striped": self.fail_exact_striped_cb.isChecked(),
            "highlight_perfect": self.highlight_perfect_cb.isChecked(),
            "perfect_include_hard": self.perfect_include_hard_cb.isChecked(),
            "perfect_color": self.colors.get("perfect_color", "#FFD700")
        }
        
        # Build Text Options
        def build_conf(widgets):
            return {
                "enabled": widgets["enabled"].isChecked(),
                "type": widgets["type"].currentText(),
                "count_direction": widgets["dir"].currentText(),
                "style": {
                    "color": widgets["color"].property("hex_color"),
                    "bold": widgets["bold"].isChecked(),
                    "outline": widgets["outline"].isChecked(),
                    "outline_color": widgets["outline_color"].property("hex_color")
                }
            }
            
        self.config["text_options"] = {
            "top": {
                "numbers": build_conf(self.top_num_widgets),
                "percentages": build_conf(self.top_pct_widgets)
            },
            "bottom": {
                "numbers": build_conf(self.bot_num_widgets),
                "percentages": build_conf(self.bot_pct_widgets)
            }
        }
        
        # Timer
        def build_timer_conf(widgets):
            return {
                "enabled": widgets["enabled"].isChecked(),
                "live_enabled": widgets["live"].isChecked(),
                "format": {
                    "minutes": widgets["minutes"].isChecked(),
                    "seconds": widgets["seconds"].isChecked(),
                    "milliseconds": widgets["milliseconds"].isChecked()
                },
                "style": {
                    "color": widgets["color"].property("hex_color"),
                    "bold": widgets["bold"].isChecked(),
                    "outline": widgets["outline"].isChecked(),
                    "outline_color": widgets["outline_color"].property("hex_color")
                }
            }

        self.config["timer"] = {
            "use_anki_cap": self.timer_cap.isChecked(),
            "chunk_timer": build_timer_conf(self.chunk_timer_widgets),
            "card_timer": build_timer_conf(self.card_timer_widgets)
        }
        
        mw.addonManager.writeConfig(__name__, self.config)
        super().accept()
