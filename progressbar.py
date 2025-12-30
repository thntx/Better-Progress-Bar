
from aqt.qt import *
from aqt import mw
import time

class ProgressBarWidget(QWidget):
    def __init__(self, bar_type="chunks"):
        super().__init__()
        self.bar_type = bar_type
        self.setFixedHeight(20) # Single bar height
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setMouseTracking(True)
        
        self.total = 0
        self.current = 0
        self.chunk_size = 10 # Default changed from 5 to 10
        self.status_log = []
        self.time_log = []
        self.start_time = 0
        
        self.config = {} # Will hold full config
        self.colors = { # Default colors, will be updated by config
            "good": QColor("#66cc66"),
            "hard": QColor("#EEDD88"),
            "easy": QColor("#AA88DD"),
            "again": QColor("#ff6666"),
            "again_chunk": QColor("#984B4B"),
            "undo": QColor("#404040"),
            "current_chunk": QColor("#66aadd"),
            "future": QColor("#303030")
        }
        self.text_config = { # Default text config, will be updated by config
            "top": {
                "numbers": {"enabled": True, "type": "absolute", "count_direction": "done"},
                "percentages": {"enabled": True, "type": "total", "count_direction": "done"}
            },
            "bottom": {
                "numbers": {"enabled": True, "type": "relative", "count_direction": "remaining"},
                "percentages": {"enabled": True, "type": "total", "count_direction": "done"}
            },
            "style": {"color": "#ffffff", "bold": False, "outline": False, "outline_color": "#000000"}
        }
        self.timer_conf = {}
        self.is_hovering = False
        self.hover_index = -1
        self.hover_callback = None  # Callback to notify other widget of hover state
        
        # Live Timer Trigger
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        # Check timer config to start/stop provided in update_config

    def enterEvent(self, event):
        self.is_hovering = True
        if self.hover_callback:
            self.hover_callback(True)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.is_hovering = False
        self.hover_index = -1
        if self.hover_callback:
            self.hover_callback(False)
        self.update()
        super().leaveEvent(event)
    
    def set_hover_state(self, is_hovering):
        """Called by sibling widget to synchronize hover state"""
        self.is_hovering = is_hovering
        if not is_hovering:
            self.hover_index = -1
        self.update()

    def set_params(self, total, current, status_log=[], time_log=[], start_time=0, initial_total=None):
        self.total = total
        self.current = current
        self.status_log = status_log
        self.time_log = time_log
        self.start_time = start_time
        # Track original total for excess calculation
        # If initial_total is not provided, assume current total is the initial
        self.initial_total = initial_total if initial_total is not None else total
        self.update()

    def update_config(self, config):
        self.chunk_size = config.get("chunk_size", 5)
        colors = config.get("colors", {})
        
        # Legacy Support: Rename 'done' to 'good' if 'good' missing
        good_val = colors.get("good", colors.get("done", "#66cc66"))
        
        self.colors["good"] = QColor(good_val)
        self.colors["hard"] = QColor(colors.get("hard", "#EEDD88"))
        self.colors["easy"] = QColor(colors.get("easy", "#AA88DD"))
        
        # Legacy: Rename 'fail' to 'again'
        again_val = colors.get("again", colors.get("fail", "#ff6666"))
        self.colors["again"] = QColor(again_val)
        
        again_chunk_val = colors.get("again_chunk", colors.get("fail_chunk", "#984B4B"))
        self.colors["again_chunk"] = QColor(again_chunk_val)
        
        self.colors["undo"] = QColor(colors.get("undo", "#404040"))
        self.colors["current_chunk"] = QColor(colors.get("current_chunk", "#66aadd"))
        self.colors["future"] = QColor(colors.get("future", "#303030"))
        
        new_text_conf = config.get("text_options", {})
        # Deep modify or careful update?
        # Let's ensure default style is preserved if missing
        if "style" not in new_text_conf and "style" in self.text_config:
             new_text_conf["style"] = self.text_config["style"]
             
        # Actually safer to just update keys? 
        # But structure might differ. 
        # Let's assume user config structure matches default
        self.text_config = new_text_conf
        
        # Ensure fallback defaults exist at top level
        default_defaults = {
            "style": {"color": "#ffffff", "bold": False, "outline": False, "outline_color": "#000000"}
        }
        if "style" not in self.text_config:
            self.text_config["style"] = default_defaults["style"]
        else:
             # Merge specific style keys if missing
             for k, v in default_defaults["style"].items():
                 if k not in self.text_config["style"]:
                     self.text_config["style"][k] = v
        self.timer_conf = config.get("timer", {})
        
        # Check if we need live timer running
        chunk_live = self.timer_conf.get("chunk_timer", {}).get("live_enabled", False)
        card_live = self.timer_conf.get("card_timer", {}).get("live_enabled", False)
        
        if chunk_live or card_live:
             if not self.timer.isActive():
                 self.timer.start(100) # 100ms update
        else:
             self.timer.stop()

        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.settings_callback:
            self.settings_callback()

    def get_text_pen(self, style_conf):
        c = QColor(style_conf.get("color", "#ffffff"))
        return QPen(c)

    def config_font(self, painter, rect_height, style_conf, bold_override=False):
        font = painter.font()
        font.setPixelSize(int(rect_height * 0.75))
        is_bold = style_conf.get("bold", False) or bold_override
        font.setBold(is_bold)
        painter.setFont(font)
        return font

    def draw_styled_text(self, painter, rect, text, style_conf, alignment=Qt.AlignmentFlag.AlignCenter, auto_hide=False):
        if not text: return
        
        # Setup Font
        font = self.config_font(painter, rect.height(), style_conf)
        
        fm = QFontMetrics(font)
        text_w = fm.horizontalAdvance(text)
        
        # Auto-Hide Logic
        if auto_hide:
            # 2px padding
            if text_w > (rect.width() - 2):
                return
        
        # Outline logic using PainterPath
        path = QPainterPath()
        text_h = fm.height()
        ascent = fm.ascent()
        
        # Calculate center
        x = rect.x() + (rect.width() - text_w) / 2
        y = rect.y() + (rect.height() - text_h) / 2 + ascent
        
        path.addText(x, y, font, text)
        
        if style_conf.get("outline", False):
            o_col = QColor(style_conf.get("outline_color", "#000000"))
            pen = QPen(o_col)
            pen.setWidth(3)
            painter.strokePath(path, pen)
            
        color = QColor(style_conf.get("color", "#ffffff"))
        painter.fillPath(path, QBrush(color))

    def get_display_value(self, index, max_val, type_mode, is_chunk_bar, chunk_start=0):
        key = "top" if is_chunk_bar else "bottom"
        conf = self.text_config.get(key, {}).get("numbers", {})
        direction = conf.get("count_direction", "done")
        
        val = 0
        if direction in ["done", "passed"]:
            # Standard counting 1..N
            if type_mode == "relative":
                val = index + 1
            else: # Absolute
                if is_chunk_bar:
                     # Cumulative Cards (e.g., 10, 20, 30...)
                    val = min((index + 1) * self.chunk_size, self.total)
                else:
                    # Global Card Index
                    val = chunk_start + index + 1
        else: # Remaining
            # Countdown: N..1
            if type_mode == "relative":
                val = max_val - index
            else: # Absolute
                if is_chunk_bar:
                    # Cards remaining at START of chunk (e.g., 30, 20, 10...)
                    val = max(0, self.total - (index * self.chunk_size))
                else:
                    # Cards remaining at START of card slot
                    val = self.total - (chunk_start + index)
        return str(val)

    def fmt_duration(self, seconds, fmt_conf):
        if seconds is None: return ""
        
        parts = []
        
        # Minutes
        if fmt_conf.get("minutes", False):
            m = int(seconds // 60)
            seconds = seconds % 60
            parts.append(f"{m}m")
            
        # Seconds
        s_en = fmt_conf.get("seconds", True)
        ms_en = fmt_conf.get("milliseconds", False)
        
        if s_en:
            if ms_en:
                val = f"{seconds:.3f}"
                parts.append(f"{val}s")
            else:
                parts.append(f"{int(seconds)}s")
        elif ms_en:
             ms = int((seconds - int(seconds)) * 1000)
             parts.append(f"{ms}ms")
             
        return " ".join(parts).strip()

    def draw_rect_pattern(self, painter, rect, bg_color, fg_color):
        painter.fillRect(rect, bg_color)
        
        painter.save()
        painter.setClipRect(rect)
        
        # Draw striped pattern manually for equal width control
        # We want 50/50 ratio.
        # W = 4. Step = 11 (approx 2W * sqrt(2))
        pen_width = 4
        step = 11
        
        pen = QPen(fg_color)
        pen.setWidth(pen_width)
        painter.setPen(pen)
        
        h = rect.height()
        # Ensure we cover the whole rect including diagonals
        start_x = int(rect.left()) - int(h) - step
        end_x = int(rect.right()) + step
        
        for x in range(start_x, end_x, step):
            # Draw Diagonal /
            p1 = QPointF(x, rect.bottom())
            p2 = QPointF(x + h, rect.top())
            painter.drawLine(p1, p2)
            
        painter.restore()

    def paintEvent(self, event):
        if self.total <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        width = rect.width()
        height = rect.height()
        bar_height = height 
        
        # Configs
        config = mw.addonManager.getConfig(__name__)
        fail_policy = config.get("fail_policy", "ignore")
        vis_opts = config.get("visual_options", {})
        auto_hide = vis_opts.get("auto_hide_text", False) # Restore auto_hide
        
        chunk_timer = config.get("timer", {}).get("chunk_timer", {})
        card_timer = config.get("timer", {}).get("card_timer", {})
        
        width = self.width()
        height = self.height()
        bar_height = height # Simple fill
        
        # Helper to resolve styles
        def resolve_style(specific, global_def):
            s = global_def.copy()
            s.update(specific)
            return s
            
        default_style = self.text_config.get("style", {})

        # --- CHUNKS BAR ---
        if self.bar_type == "chunks":
            import math
            import time
            # Use initial_total (original total at session start) for excess calculation
            # If initial_total wasn't set, fall back to self.total
            normal_total = getattr(self, 'initial_total', self.total)
            # Ensure bar grows if total (including fails) exceeds initial total
            # Use self.total here, not self.current, so the bar grows immediately when cards are failed
            effective_total = max(normal_total, self.total)
            total_chunks = (effective_total + self.chunk_size - 1) // self.chunk_size
            if total_chunks < 1: total_chunks = 1
            
            current_chunk_idx = self.current // self.chunk_size
            
            chunk_w = width / total_chunks
            
            # --- Text Config ---
            # Read from text_options.top for chunks bar
            top_text_conf = self.text_config.get("top", {})
            numbers_conf = top_text_conf.get("numbers", {})
            percent_conf = top_text_conf.get("percentages", {})
            
            tn_en = numbers_conf.get("enabled", True)
            tn_type = numbers_conf.get("type", "total")
            tn_style = resolve_style(numbers_conf.get("style", {}), default_style)
            tp_en = percent_conf.get("enabled", True)
            tp_type = percent_conf.get("type", "total") 
            tp_dir = percent_conf.get("count_direction", "done")
            tp_style = resolve_style(percent_conf.get("style", {}), default_style)
            
            chunk_timer_en = chunk_timer.get("enabled", False)
            chunk_live_en = chunk_timer.get("live_enabled", False)
            
            t_num_en = tn_en
            t_num_type = tn_type
            t_pct_en = tp_en
            t_pct_type = tp_type
            t_pct_dir = tp_dir
            
            # Pre-calculate Top Centered Text to Find Safe Zone
            centered_str_top = ""
            c_style_top = tn_style
            
            parts_top = []
            
            # Check if we should show total text (centered)
            # Show total text when NOT hovering, OR when hovering but there's no relative/absolute text to show
            has_relative_text = (t_num_en and t_num_type != "total") or (t_pct_en and t_pct_type != "total")
            show_total_text = not self.is_hovering or not has_relative_text
            
            if show_total_text:
                # Show total text (centered)
                if t_num_en and t_num_type == "total":
                    direction = numbers_conf.get("count_direction", "done") 
                    # Use effective total chunks for accurate "Remaining" count?
                    val = current_chunk_idx + 1 if direction in ["done", "passed"] else total_chunks - current_chunk_idx
                    parts_top.append(str(val))
                    c_style_top = tn_style
                
                if t_pct_en and t_pct_type == "total":
                    ratio = self.current / self.total if self.total > 0 else 0
                    # For total text, we use actual total which shows progress against all work
                    val = int(ratio * 100)
                    if t_pct_dir == "remaining": val = 100 - val
                    parts_top.append(f"{val}%")
                    if not (t_num_en and t_num_type == "total"):
                         c_style_top = tp_style
            
            top_safe_zone = QRectF()
            if parts_top:
                centered_str_top = " - ".join(parts_top)
                # Measure text width
                temp_font = self.config_font(painter, bar_height, c_style_top)
                fm = QFontMetrics(temp_font)
                text_width = fm.horizontalAdvance(centered_str_top)
                # Define safe zone with padding
                padding = 4
                left_x = (width - text_width) / 2 - padding
                top_safe_zone = QRectF(left_x, 0, text_width + 2*padding, bar_height)


                # Pre-calculate symmetric skips
            # All-or-Nothing Auto Hide (Chunks)
            hide_all_chunk_text = False
            if vis_opts.get("auto_hide_text", False):
                 # Sample most likely scenario for overflow
                 # Number strings usually at most 4-5 digits (including timer)
                 s_parts = []
                 # 1. Check relative number (e.g. 99)
                 if t_num_en and t_num_type != "total": s_parts.append(str(total_chunks))
                 # 2. Check percentage (e.g. 100%)
                 if t_pct_en and t_pct_type != "total": s_parts.append("100%")
                 # 3. Check timer (e.g. 99s)
                 if chunk_timer_en: s_parts.append("99s") 
                 
                 if s_parts:
                     temp_font = self.config_font(painter, bar_height, tn_style)
                     # Check if total width of all enabled parts exceeds cell width
                     # Space-delimited if multiple
                     sample_str = " ".join(s_parts)
                     if QFontMetrics(temp_font).horizontalAdvance(sample_str) > chunk_w:
                         hide_all_chunk_text = True

            # 2. All-or-Nothing Collision Detection (Symmetry) - REVERTED TO INDIVIDUAL
            # We keep hide_all_chunk_text for width, but we don't hide the whole bar for a single overlap.
            # This allows the side numbers to stay visible unless they themselves hit the middle text.

                         
            # Draw Top Chunks
            has_total_top = bool(centered_str_top)
            
            # --- VISUAL OPTIONS LIFT ---
            hl_excess = vis_opts.get("highlight_excess", True)
            str_again = vis_opts.get("striped_again", False) 
            # Note: str_excess is now removed, striping is default for mixed excess if hl_excess is True
            for i in range(total_chunks):
                x = i * chunk_w
                rect_f = QRectF(x, 0, chunk_w - 1, bar_height - 1)
                
                # Base Colors & Logic
                c_start = i * self.chunk_size
                c_end = (i + 1) * self.chunk_size
                
                # Identify special states
                is_mixed_excess = False
                is_mixed_fail = False
                is_mixed_undo = False
                has_all_fail = False
                fail_count = 0
                undo_count = 0
                
                # Check Mixed Excess (Pending + Excess) - ALWAYS check regardless of fail_policy
                # This is needed to visualize chunks that extend beyond normal_total
                if c_start < normal_total and c_end > normal_total:
                    is_mixed_excess = True
                
                if fail_policy in ["count", "acknowledge"]: # updated check
                    # Check Mixed Fail (Done + Fail)
                    if i < current_chunk_idx:
                        # Check log for fails
                        safe_end = min(c_end, len(self.status_log))
                        if c_start < safe_end:
                             chunk_slice = self.status_log[c_start:safe_end]
                             # 1 = Fail, but True = 1. Must check type for True.
                             fails = [x for x in chunk_slice if (x == 1 and x is not True) or x is False]
                             if fails:
                                 if len(fails) == len(chunk_slice):
                                     has_all_fail = True
                                 else:
                                     is_mixed_fail = True
                                 fail_count = len(fails)
                                     
                             undos = [x for x in chunk_slice if x == "undone"]
                             if undos:
                                 undo_count = len(undos)
                                 # Check All Undo
                                 # ... logic handled later
                                 is_mixed_undo = True

                # Apply Color
                # Apply Color
                if i < current_chunk_idx:
                    safe_end = min(c_end, len(self.status_log))
                    chunk_slice = self.status_log[c_start:safe_end]
                    
                    only_pass_fail = vis_opts.get("only_pass_fail", False)
                    u_good_pass = vis_opts.get("use_good_for_all_pass", False)
                    
                    # 1. Calculate Scores/Stats
                    scores = []
                    fails = 0
                    hards = 0
                    for s in chunk_slice:
                        # Map Status to Score
                        # Again=1, Hard=2, Good=3, Easy=4
                        score = 3 # Default Good
                        if s is False or s == 1: 
                            score = 1
                            fails += 1
                        elif s == 2: 
                            score = 2
                            hards += 1
                        elif s == 3 or s is True: score = 3
                        elif s == 4: 
                            score = 4
                        elif s == "undone": 
                            score = 1 # Treat undone as fail for avg
                            fails += 1
                        
                        scores.append(score)
                    
                    avg = sum(scores) / len(scores) if scores else 3.0
                    
                    # 2. Determine Color
                    # ... (color determination logic remains the same)
                    final_color = self.colors["good"]
                    pattern_color = None # For stripes
                    
                    if only_pass_fail:
                        # Threshold Logic
                        th_op = vis_opts.get("fail_threshold_op", "gt")
                        th_val = vis_opts.get("fail_threshold_val", 50)
                        th_unit = vis_opts.get("fail_threshold_unit", "%")
                        th_exact_str = vis_opts.get("fail_exact_striped", True)
                        
                        calc_val = fails
                        if th_unit == "%":
                            calc_val = (fails * 100) / len(chunk_slice) if chunk_slice else 0
                        
                        is_fail = False
                        is_exact = False
                        if th_op == "gt":
                            is_fail = calc_val > th_val
                        else:
                            is_fail = calc_val >= th_val
                        
                        if th_exact_str and abs(calc_val - th_val) < 0.001:
                            is_exact = True
                        
                        if is_fail:
                            final_color = self.colors["again"]
                        elif is_exact:
                            final_color = self.colors["good"]
                            pattern_color = self.colors["again"]
                        else:
                            final_color = self.colors["good"]
                    else:
                        # Average Logic
                        if avg < 1.5:
                            final_color = self.colors["again"]
                        elif abs(avg - 1.5) < 0.001:
                            final_color = self.colors["hard"]
                            pattern_color = self.colors["again"]
                        elif avg < 2.5:
                            final_color = self.colors["hard"]
                        elif abs(avg - 2.5) < 0.001:
                            final_color = self.colors["good"]
                            pattern_color = self.colors["hard"]
                        elif avg < 3.5:
                            final_color = self.colors["good"]
                        elif abs(avg - 3.5) < 0.001:
                            final_color = self.colors["easy"]
                            pattern_color = self.colors["good"]
                        else:
                            final_color = self.colors["easy"]

                    # 3. Paint
                    if pattern_color:
                        self.draw_rect_pattern(painter, rect_f, final_color, pattern_color)
                    else:
                        painter.fillRect(rect_f, final_color)
                    
                    # 4. Perfect Highlight (Outline)
                    is_perfect = (fails == 0)
                    if vis_opts.get("perfect_include_hard", True) and hards > 0:
                        is_perfect = False
                        
                    if vis_opts.get("highlight_perfect", False) and is_perfect:
                        p_color = self.colors.get("perfect_color", "#FFD700")
                        painter.save()
                        pen = QPen(QColor(p_color))
                        pen.setWidth(4)
                        painter.setPen(pen)
                        # Draw inner outline
                        painter.drawRect(rect_f.adjusted(2, 2, -2, -2))
                        painter.restore()
                elif i == current_chunk_idx:
                    painter.fillRect(rect_f, self.colors["current_chunk"])
                else:
                    # Future chunks (not yet completed)
                    # Check if this is an excess chunk (beyond original total)
                    if c_start >= normal_total:
                        # Fully excess future chunk - solid color
                        if hl_excess:
                            painter.fillRect(rect_f, self.colors["again_chunk"])
                        else:
                            painter.fillRect(rect_f, self.colors["future"])
                    elif is_mixed_excess:
                        # Mixed excess future chunk - partially contains excess cards
                        # Automatically stripe if highlight is on
                        if hl_excess:
                            # Stripe: future background with again_chunk foreground
                            self.draw_rect_pattern(painter, rect_f, self.colors["future"], self.colors["again_chunk"])
                        else:
                            painter.fillRect(rect_f, self.colors["future"])
                    else:
                        # Normal future chunk
                        painter.fillRect(rect_f, self.colors["future"])
                
                
                # Determine what text would be shown
                # Render individual chunk text
                if not hide_all_chunk_text:
                    cur_n_style = tn_style
                    cur_p_style = tp_style
                    
                    # 1. Determine base visibility/content (relative/absolute)
                    show_num_chunk = (t_num_en and t_num_type != "total")
                    show_pct_chunk = (t_pct_en and t_pct_type != "total")
                    
                    num_str_chunk = ""
                    pct_str_chunk = ""
                    if show_num_chunk: num_str_chunk = self.get_display_value(i, total_chunks, t_num_type, True)
                    if show_pct_chunk:
                        if t_pct_dir == "remaining":
                            rem_cards = max(0, self.total - (i * self.chunk_size))
                            ratio_calc = rem_cards / self.total if self.total > 0 else 0
                        else:
                            c_end_c = (i + 1) * self.chunk_size
                            ratio_calc = min(c_end_c, self.total) / self.total if self.total > 0 else 0
                        pct_str_chunk = f"{int(ratio_calc * 100)}%"

                    # 2. Check for Timer Overrides
                    override_time_str = None
                    if chunk_timer_en and i < current_chunk_idx:
                        c_time = sum(self.time_log[c_start : min(c_end, len(self.time_log))])
                        if c_time > 0:
                            override_time_str = self.fmt_duration(c_time, chunk_timer.get("format", {}))
                            cur_n_style = chunk_timer.get("style", tn_style)
                    elif chunk_live_en and i == current_chunk_idx:
                         if self.start_time > 0:
                             # Current card elapsed
                             elapsed = time.time() - self.start_time
                             # Sum of previous cards in THIS chunk
                             prev_sum = sum(self.time_log[c_start : self.current])
                             total_chunk_time = prev_sum + elapsed
                             
                             if total_chunk_time > 0:
                                 override_time_str = self.fmt_duration(total_chunk_time, chunk_timer.get("format", {}))
                                 cur_n_style = chunk_timer.get("style", tn_style)

                    if override_time_str:
                        num_str_chunk = override_time_str
                        pct_str_chunk = ""
                        show_num_chunk = True
                        show_pct_chunk = False

                    # 3. Individual Collision Detection
                    if has_total_top and (show_num_chunk or show_pct_chunk):
                        fm = QFontMetrics(self.config_font(painter, bar_height, cur_n_style))
                        sample_full = " ".join([parts for parts in [num_str_chunk, pct_str_chunk] if parts])
                        tw_calc = fm.horizontalAdvance(sample_full)
                        tx_calc = i * chunk_w + (chunk_w - tw_calc) / 2
                        if QRectF(tx_calc - 2, 0, tw_calc + 4, bar_height).intersects(top_safe_zone):
                            show_num_chunk = show_pct_chunk = False

                    # 4. Rendering
                    if show_num_chunk and show_pct_chunk:
                        r_num = QRectF(x, 0, chunk_w/2, bar_height - 1)
                        r_pct = QRectF(x + chunk_w/2, 0, chunk_w/2, bar_height - 1)
                        self.draw_styled_text(painter, r_num, num_str_chunk, cur_n_style, auto_hide=False)
                        self.draw_styled_text(painter, r_pct, pct_str_chunk, cur_p_style, auto_hide=False)
                    elif show_num_chunk:
                        self.draw_styled_text(painter, rect_f, num_str_chunk, cur_n_style, auto_hide=False)
                    elif show_pct_chunk:
                        self.draw_styled_text(painter, rect_f, pct_str_chunk, cur_p_style, auto_hide=False)


            # Draw Top Centered Text
            if centered_str_top:
                self.draw_styled_text(painter, QRectF(0, 0, width, bar_height), centered_str_top, c_style_top, auto_hide=auto_hide)


        # --- CARDS BAR ---
        elif self.bar_type == "chunks": # Defensive check, but we are in elif
             pass
        else: # cards
            # Chunk Zoom Mode (Cards Bar)
            chunk_size = self.chunk_size
            current_chunk_idx = self.current // chunk_size
            start_offset = current_chunk_idx * chunk_size
            
            # Show only the cards that exist in this chunk
            normal_total = getattr(self, 'initial_total', self.total)
            effective_total_c = max(normal_total, self.total)
            total_items = min(chunk_size, max(0, effective_total_c - start_offset))
            if total_items < 1: total_items = 1
            
            # Re-read Timer Config for Cards
            card_timer = self.timer_conf.get("card_timer", {}) # Ensure card_timer is defined here
            
            # Read from text_options.bottom for cards bar
            bottom_text_conf = self.text_config.get("bottom", {})
            numbers_conf = bottom_text_conf.get("numbers", {})
            percent_conf = bottom_text_conf.get("percentages", {})
            
            tn_en = numbers_conf.get("enabled", True)
            tn_type = numbers_conf.get("type", "total")
            tn_style = resolve_style(numbers_conf.get("style", {}), default_style)
            tp_en = percent_conf.get("enabled", True)
            tp_type = percent_conf.get("type", "total") 
            tp_dir = percent_conf.get("count_direction", "done")
            tp_style = resolve_style(percent_conf.get("style", {}), default_style)
            
            card_timer_en = card_timer.get("enabled", False)
            card_live_en = card_timer.get("live_enabled", False)
            import time # Ensure time is imported here if not globally
            
            item_w = width / total_items
            
            # Determine Top Text (Safe Zone)
            centered_str_top = ""
            c_style_top = tn_style
            parts_top = []
            
            # Check if we should show total text (centered)
            # Show total text when NOT hovering, OR when hovering but there's no relative/absolute text to show
            has_relative_text = (tn_en and tn_type != "total") or (tp_en and tp_type != "total")
            show_total_text = not self.is_hovering or not has_relative_text
            
            if show_total_text:
                # Show total text (centered)
                if tn_en and tn_type == "total":
                    direction = numbers_conf.get("count_direction", "done")
                    # Relative numbering for cards in current chunk
                    chunk_pos = self.current - start_offset
                    val = (chunk_pos + 1) if direction in ["done", "passed"] else (total_items - chunk_pos)
                    parts_top.append(str(val))
                    c_style_top = tn_style
                    
                if tp_en and tp_type == "total":
                    # For cards bar percentage, show progress in current chunk
                    chunk_start = current_chunk_idx * chunk_size
                    # Cap current at end of chunk for percentage display
                    cards_done_in_chunk = self.current - chunk_start
                    ratio = cards_done_in_chunk / chunk_size if chunk_size > 0 else 0
                    val = int(ratio * 100)
                    if tp_dir == "remaining": val = 100 - val
                    parts_top.append(f"{val}%")
                    if not (tn_en and tn_type == "total"):
                         c_style_top = tp_style
            
            top_safe_zone = QRectF()
            if parts_top:
                centered_str_top = " - ".join(parts_top)
                temp_font = self.config_font(painter, bar_height, c_style_top)
                fm = QFontMetrics(temp_font)
                text_width = fm.horizontalAdvance(centered_str_top)
                padding = 4
                left_x = (width - text_width) / 2 - padding
                top_safe_zone = QRectF(left_x, 0, text_width + 2*padding, bar_height)
            
            # Draw Cards
            has_total_top = bool(centered_str_top)
            
            # Define auto_hide for cards bar
            auto_hide = vis_opts.get("auto_hide_text", False)
            hl_excess = vis_opts.get("highlight_excess", True)
            str_again = vis_opts.get("striped_again", False)

            # All-or-Nothing Auto Hide (Cards)
            hide_all_card_text = False
            if auto_hide:
                 # Sample most likely scenario for overflow
                 s_parts = []
                 # 1. Check relative number (e.g. 10)
                 if tn_en and tn_type != "total": s_parts.append(str(total_items))
                 # 2. Check percentage (e.g. 100%)
                 if tp_en and tp_type != "total": s_parts.append("100%")
                 # 3. Check card timer (e.g. 99s)
                 if card_timer_en: s_parts.append("99s") 
                 
                 if s_parts:
                     temp_font = self.config_font(painter, bar_height, tn_style)
                     # Check if total width of all enabled parts exceeds cell width
                     sample_str = " ".join(s_parts)
                     if QFontMetrics(temp_font).horizontalAdvance(sample_str) > item_w:
                         hide_all_card_text = True
            
            # 2. All-or-Nothing Collision Detection (Symmetry) - REVERTED TO INDIVIDUAL
            # Individual collision detection is handled inside the rendering loop.

            
            for i in range(total_items):
                x = i * item_w
                rect_f = QRectF(x, 0, item_w - 1, bar_height - 1)
                
                # For 'cards' bar showing all cards, global index is just i
                global_idx = start_offset + i
                
                # Colors
                # Colors
                if global_idx < self.current:
                    try:
                        color = self.colors["good"]
                        if global_idx < len(self.status_log):
                            stat = self.status_log[global_idx]
                            
                            u_good_pass = vis_opts.get("use_good_for_all_pass", False)
                            # Handle Legacy Bools
                            if stat is True: color = self.colors["good"]
                            elif stat is False: color = self.colors["again"]
                            elif stat == 1: color = self.colors["again"]
                            elif stat == 2: color = self.colors["good"] if u_good_pass else self.colors["hard"]
                            elif stat == 3: color = self.colors["good"]
                            elif stat == 4: color = self.colors["good"] if u_good_pass else self.colors["easy"]
                            elif stat == "undone": color = self.colors["undo"]
                        
                        painter.fillRect(rect_f, color)
                    except Exception:
                         # Fallback
                         painter.fillRect(rect_f, self.colors["good"])
                elif global_idx == self.current:
                    # Current card being reviewed
                    painter.fillRect(rect_f, self.colors["current_chunk"])
                else:
                    # Future cards in this chunk
                    painter.fillRect(rect_f, self.colors["future"])
                    
                # Render Individual Card Text (if not hidden)
                if not hide_all_card_text:
                    cur_n_style = tn_style
                    cur_p_style = tp_style
                    
                    # 1. Determine base visibility/content
                    show_num_card = (tn_en and tn_type != "total")
                    show_pct_card = (tp_en and tp_type != "total")
                    
                    num_str_card = ""
                    pct_str_card = ""
                    if show_num_card: num_str_card = str(i + 1)
                    if show_pct_card:
                        ratio_calc = (i + 1) / total_items if total_items > 0 else 0
                        val_calc = int(ratio_calc * 100)
                        if tp_dir == "remaining": val_calc = 100 - val_calc
                        pct_str_card = f"{val_calc}%"

                    # 2. Check for Timer Overrides
                    override_time_str = None
                    if card_timer_en and global_idx < len(self.time_log):
                        t_card = self.time_log[global_idx]
                        if t_card > 0:
                            override_time_str = self.fmt_duration(t_card, card_timer.get("format", {}))
                            cur_n_style = card_timer.get("style", tn_style)
                    elif card_live_en and global_idx == self.current:
                        if self.start_time > 0:
                            elapsed_card = time.time() - self.start_time
                            override_time_str = self.fmt_duration(elapsed_card, card_timer.get("format", {}))
                            cur_n_style = card_timer.get("style", tn_style)

                    if override_time_str:
                        num_str_card = override_time_str
                        pct_str_card = ""
                        show_num_card = True
                        show_pct_card = False

                    # 3. Individual Collision Detection
                    if has_total_top and (show_num_card or show_pct_card):
                         fm = QFontMetrics(self.config_font(painter, bar_height, cur_n_style))
                         sample_full_card = " ".join([p for p in [num_str_card, pct_str_card] if p])
                         tw_calc_card = fm.horizontalAdvance(sample_full_card)
                         tx_calc_card = i * item_w + (item_w - tw_calc_card) / 2
                         if QRectF(tx_calc_card - 2, 0, tw_calc_card + 4, bar_height).intersects(top_safe_zone):
                             show_num_card = show_pct_card = False

                    # 4. Rendering
                    if show_num_card and show_pct_card:
                        r_num = QRectF(x, 0, item_w/2, bar_height - 1)
                        r_pct = QRectF(x + item_w/2, 0, item_w/2, bar_height - 1)
                        self.draw_styled_text(painter, r_num, num_str_card, cur_n_style, auto_hide=False)
                        self.draw_styled_text(painter, r_pct, pct_str_card, cur_p_style, auto_hide=False)
                    elif show_num_card:
                        self.draw_styled_text(painter, rect_f, num_str_card, cur_n_style, auto_hide=False)
                    elif show_pct_card:
                        self.draw_styled_text(painter, rect_f, pct_str_card, cur_p_style, auto_hide=False)


            # Draw Top Centered Text (Cards Bar)
            if centered_str_top:
                self.draw_styled_text(painter, QRectF(0, 0, width, bar_height), centered_str_top, c_style_top, auto_hide=auto_hide)
