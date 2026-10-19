"""
Basketball Shooting Animation  (Python + Tkinter Canvas, standard library only)

The scene follows the reference picture: the player stands on the RIGHT,
the hoop (backboard, rim, net, pole) is on the LEFT, and the ball flies
from the player's hands to the hoop along a curved path.

AUTOMATIC ANIMATION
    The program runs by itself. One single animation loop (tick) is started
    when the program opens, and a "state" variable decides what happens:

        DRIBBLING  -> the player bounces the ball up and down by the hand.
                      After a few dribbles the player holds the ball and ...
        SHOOTING   -> ... releases it. The ball flies in a gravity arc.
                      The program checks if the ball goes through the hoop.
        RESETTING  -> short pause so you can read SCORE / Missed.
        RETURNING  -> the ball hops back across the floor to the player.
                      Then the state goes back to DRIBBLING and it repeats.

    The "Shoot Ball" button is an optional manual control: it asks the
    player to shoot at the next moment the ball is in the hand. It never
    starts a second animation loop.

GALLERY CHALLENGE
    Question: How can you make the ball follow an arc rather than travel
              in a straight line?
    Answer:   * Horizontal velocity (vx) moves the ball toward the hoop at
                a steady speed.
              * Gravity changes the vertical velocity (vy) a little in EVERY
                frame:   vy = vy + gravity.
                The ball first rises (vy is negative), slows down, stops at
                the top of the arc (vy = 0), then falls faster and faster
                (vy is positive).
              * Steady sideways motion + a vertical speed that keeps
                changing = a curved path (a parabola).
              Without gravity (gravity = 0) the ball would go in a straight
              line. Try setting GRAVITY = 0 to see the difference!

TKINTER COORDINATE NOTE
    x grows to the RIGHT, but y grows DOWNWARD.
    So moving UP means a NEGATIVE vy, and gravity is a POSITIVE number
    (it pulls the ball toward larger y, i.e. down the screen).
    The hoop is on the LEFT, so the ball moves LEFT: vx is NEGATIVE.
"""

import math
import random
import tkinter as tk
from tkinter import messagebox

# ----------------------------------------------------------------------
# Settings you can change
# ----------------------------------------------------------------------
CANVAS_WIDTH = 900
CANVAS_HEIGHT = 540
FLOOR_Y = 500                # y position of the court floor

FRAME_DELAY_MS = 20          # time between frames (20 ms = 50 frames per second)
GRAVITY = 0.5                # downward acceleration added to vy every frame

DEFAULT_ANGLE = 60           # shooting angle in degrees (slider start value)
DEFAULT_POWER = 19.5         # launch speed (slider start value)
POWER_VARIATION = 1.2        # automatic shots change power by up to +/- this much

BALL_RADIUS = 15
BALL_START_X = 650           # the ball is held / released here (by the hands)
BALL_START_Y = 360

# Dribbling
DRIBBLES_BEFORE_SHOT = 4     # how many dribbles before the automatic shot
DRIBBLE_PUSH_SPEED = 6.0     # downward speed the hand gives the ball
HOLD_FRAMES = 14             # frames the player holds the ball before shooting

# Pauses and return trip
RESET_PAUSE_FRAMES = 45      # pause after a shot (45 frames = 0.9 seconds)
RETURN_SPEED = 9             # horizontal speed of the ball coming back

# Hoop (front view, like the reference picture)
RIM_LEFT_X = 70              # left end of the rim
RIM_RIGHT_X = 190            # right end of the rim
RIM_Y = 180                  # y position of the rim (the basket opening)
NET_BOTTOM_Y = 250

MAX_FRAMES = 1500            # safety limit so a shot can never run forever

# Animation states
DRIBBLING = "DRIBBLING"
SHOOTING = "SHOOTING"
RESETTING = "RESETTING"
RETURNING = "RETURNING"

# Player's arm positions: (x, y) of the two hands. Shoulders are fixed.
SHOULDER_NEAR = (725, 355)
SHOULDER_FAR = (725, 378)
POSE_SHOOT_HOLD = ((672, 350), (672, 378))     # both hands on the ball
POSE_FOLLOW_THROUGH = ((640, 300), (690, 398))  # arm up after release
POSE_REST = ((652, 343), (690, 398))           # ready to dribble

# Colours
SKY = "#e8f6fb"
FLOOR = "#c68642"
FLOOR_LINE = "#8d5a2b"
RED = "#c0392b"
BALL_COLOR = "#e8964a"
BALL_LINE = "#7a3b0c"
SKIN = "#f8c8a0"


class BasketballGame:
    """Draws the scene, runs the automatic animation and keeps the score."""

    def __init__(self, root):
        self.root = root
        self.root.title("Basketball Shooting Animation")
        self.root.resizable(False, False)

        # --- game state ---
        self.state = DRIBBLING
        self.score = 0
        self.shots = 0
        self.scored_this_shot = False  # makes sure only ONE point per shot
        self.hit_rim = False           # rim bounce happens once per shot
        self.frame_count = 0           # frames since the ball was released
        self.catch_count = 0           # how many times the hand caught the ball
        self.hold_frames = 0           # countdown while the player holds the ball
        self.pause_frames = 0          # countdown during RESETTING
        self.shoot_requested = False   # set by the Shoot button
        self.manual_shot = False       # True if the current shot was requested by button

        # --- ball position and physics variables ---
        self.x = BALL_START_X          # horizontal position
        self.y = BALL_START_Y          # vertical position
        self.vx = 0.0                  # horizontal velocity
        self.vy = DRIBBLE_PUSH_SPEED   # vertical velocity (starts moving down)
        self.gravity = GRAVITY         # downward acceleration

        # Speed the ball needs after bouncing off the floor to rise exactly
        # back to the hand (from v^2 = v0^2 + 2 * g * distance).
        drop = FLOOR_Y - BALL_RADIUS - BALL_START_Y
        self.dribble_bounce_speed = math.sqrt(
            DRIBBLE_PUSH_SPEED ** 2 + 2 * GRAVITY * drop)

        # Current hand positions (they move smoothly toward a target pose)
        self.hand_near = POSE_REST[0]
        self.hand_far = POSE_REST[1]

        self.build_widgets()
        self.draw_scene()
        self.update_score_display()
        self.show_message("Dribbling...")
        self.update_arms()

        # Start the ONE animation loop. tick() schedules itself with after().
        self.tick()

    # ------------------------------------------------------------------
    # User interface (canvas, sliders, Shoot button)
    # ------------------------------------------------------------------
    def build_widgets(self):
        # Controls are packed FIRST (at the top) so the Shoot button is always
        # visible, even on small laptop screens.
        controls = tk.Frame(self.root, padx=10, pady=8)
        controls.pack(side="top", fill="x")

        self.shoot_button = tk.Button(controls, text="Shoot Ball",
                                      font=("Arial", 14, "bold"),
                                      bg="#27ae60", fg="white",
                                      padx=14, pady=4, command=self.request_shot)
        self.shoot_button.grid(row=0, column=0, padx=(0, 18))

        tk.Label(controls, text="Angle (degrees):").grid(row=0, column=1, sticky="e")
        self.angle_scale = tk.Scale(controls, from_=30, to=80,
                                    orient="horizontal", length=140)
        self.angle_scale.set(DEFAULT_ANGLE)
        self.angle_scale.grid(row=0, column=2, padx=(4, 14))

        tk.Label(controls, text="Power:").grid(row=0, column=3, sticky="e")
        self.power_scale = tk.Scale(controls, from_=10, to=30, resolution=0.5,
                                    orient="horizontal", length=140)
        self.power_scale.set(DEFAULT_POWER)
        self.power_scale.grid(row=0, column=4, padx=(4, 14))

        # When ticked, automatic shots change a little each time (hits AND misses)
        self.vary_var = tk.BooleanVar(value=True)
        tk.Checkbutton(controls, text="Vary auto shots",
                       variable=self.vary_var).grid(row=0, column=5, padx=4)

        tk.Button(controls, text="Why an arc?", command=self.show_explanation,
                  padx=8, pady=4).grid(row=0, column=6, padx=6)

        self.canvas = tk.Canvas(self.root, width=CANVAS_WIDTH,
                                height=CANVAS_HEIGHT, bg=SKY,
                                highlightthickness=0)
        self.canvas.pack(side="top")

        # Keyboard shortcut: press the space bar to ask for a shot
        self.root.bind("<space>", lambda event: self.request_shot())

    # ------------------------------------------------------------------
    # Drawing the scene
    # ------------------------------------------------------------------
    def draw_scene(self):
        c = self.canvas

        # Floor
        c.create_rectangle(0, FLOOR_Y, CANVAS_WIDTH, CANVAS_HEIGHT,
                           fill=FLOOR, outline="")
        c.create_line(0, FLOOR_Y, CANVAS_WIDTH, FLOOR_Y, fill=FLOOR_LINE, width=3)
        for gx in range(60, CANVAS_WIDTH, 130):
            c.create_line(gx, FLOOR_Y, gx - 40, CANVAS_HEIGHT, fill=FLOOR_LINE)

        self.draw_hoop()
        self.draw_player()

        # Score display, message line and live physics readout
        c.create_rectangle(330, 12, 600, 62, fill="white", outline="#34495e", width=2)
        self.score_text = c.create_text(465, 37, text="", font=("Arial", 20, "bold"),
                                        fill="#2c3e50")
        self.message_text = c.create_text(465, 92, text="", font=("Arial", 16, "bold"),
                                          fill="#34495e")
        self.info_text = c.create_text(15, 521, anchor="w", text="",
                                       font=("Consolas", 11), fill="#4a2c0a")

        self.draw_ball()

    def draw_hoop(self):
        c = self.canvas

        # Pole and base
        c.create_rectangle(125, NET_BOTTOM_Y, 135, FLOOR_Y - 12, fill="#222222", outline="")
        c.create_rectangle(85, FLOOR_Y - 12, 175, FLOOR_Y, fill="#111111", outline="")

        # Backboard: outer red frame and inner red square (like the picture)
        c.create_rectangle(40, 30, 220, 190, fill="white", outline=RED, width=6)
        c.create_rectangle(RIM_LEFT_X, 65, RIM_RIGHT_X, RIM_Y, outline=RED, width=4)

        # Net: lines from the rim down to a narrower bottom
        top_xs = [RIM_LEFT_X + 6 + i * (RIM_RIGHT_X - RIM_LEFT_X - 12) / 6 for i in range(7)]
        bottom_xs = [RIM_LEFT_X + 28 + i * (RIM_RIGHT_X - RIM_LEFT_X - 56) / 6 for i in range(7)]
        for top_x, bottom_x in zip(top_xs, bottom_xs):
            c.create_line(top_x, RIM_Y, bottom_x, NET_BOTTOM_Y, fill="#8e9a9d")
        for i in range(1, 4):
            t = i / 4
            y = RIM_Y + t * (NET_BOTTOM_Y - RIM_Y)
            left = top_xs[0] + t * (bottom_xs[0] - top_xs[0])
            right = top_xs[-1] + t * (bottom_xs[-1] - top_xs[-1])
            c.create_line(left, y, right, y, fill="#8e9a9d")

        # Rim
        c.create_oval(RIM_LEFT_X, RIM_Y - 6, RIM_RIGHT_X, RIM_Y + 6,
                      fill="#5b1a14", outline="#5b1a14")

    def draw_player(self):
        """Draw the player. The body stays still; only the two arms move."""
        c = self.canvas

        # Legs and shoes
        c.create_line(728, 450, 700, 488, fill=SKIN, width=14, capstyle="round")
        c.create_line(765, 450, 800, 482, fill=SKIN, width=14, capstyle="round")
        c.create_oval(676, 480, 718, 498, fill="#b03a2e", outline="#7b241c")
        c.create_oval(785, 472, 827, 490, fill="#b03a2e", outline="#7b241c")

        # Shorts (with a white stripe) and tank top
        c.create_rectangle(705, 412, 790, 462, fill="#1f3a93", outline="#16275f")
        c.create_line(780, 414, 780, 460, fill="white", width=3)
        c.create_rectangle(710, 335, 785, 414, fill="#1c9bb8", outline="#12708a")

        # Arms and hands (created once, then moved with canvas.coords each frame)
        self.arm_far = c.create_line(0, 0, 0, 0, fill=SKIN, width=11, capstyle="round")
        self.arm_near = c.create_line(0, 0, 0, 0, fill=SKIN, width=11, capstyle="round")
        self.palm_far = c.create_oval(0, 0, 0, 0, fill=SKIN, outline="")
        self.palm_near = c.create_oval(0, 0, 0, 0, fill=SKIN, outline="")

        # Head: face, brown hair, ear, eye and mouth (player faces the hoop)
        c.create_oval(702, 245, 790, 333, fill=SKIN, outline="")
        c.create_arc(698, 238, 794, 322, start=0, extent=180, fill="#8e5a1f", outline="")
        c.create_rectangle(745, 280, 794, 320, fill="#8e5a1f", outline="")
        c.create_oval(756, 290, 774, 310, fill="#f2b48a", outline="")
        c.create_oval(722, 282, 731, 291, fill="#222222", outline="")
        c.create_oval(708, 304, 720, 312, fill="#e8857a", outline="")

    def draw_ball(self):
        """Draw the basketball; every part has the tag 'ball' so they move together."""
        c = self.canvas
        r = BALL_RADIUS
        x, y = BALL_START_X, BALL_START_Y
        c.create_oval(x - r, y - r, x + r, y + r, fill=BALL_COLOR,
                      outline=BALL_LINE, width=2, tags="ball")
        c.create_line(x, y - r, x, y + r, fill=BALL_LINE, tags="ball")
        c.create_line(x - r, y, x + r, y, fill=BALL_LINE, tags="ball")
        c.create_arc(x - 2.7 * r, y - 1.1 * r, x - 0.5 * r, y + 1.1 * r,
                     start=-30, extent=60, style="arc", outline=BALL_LINE, tags="ball")
        c.create_arc(x + 0.5 * r, y - 1.1 * r, x + 2.7 * r, y + 1.1 * r,
                     start=150, extent=60, style="arc", outline=BALL_LINE, tags="ball")

    # ------------------------------------------------------------------
    # Helper functions
    # ------------------------------------------------------------------
    def update_score_display(self):
        self.canvas.itemconfig(self.score_text,
                               text=f"Score: {self.score}    Shots: {self.shots}")

    def update_info_display(self):
        """Show the state and the live values of x, y, vx, vy."""
        self.canvas.itemconfig(
            self.info_text,
            text=(f"{self.state:<9}  x={self.x:6.1f}  y={self.y:6.1f}  "
                  f"vx={self.vx:6.2f}  vy={self.vy:6.2f}  gravity={self.gravity}"))

    def show_message(self, text, color="#34495e"):
        self.canvas.itemconfig(self.message_text, text=text, fill=color)

    def move_ball_to(self, new_x, new_y):
        """Move every part of the ball drawing so its centre is at (new_x, new_y)."""
        self.canvas.move("ball", new_x - self.x, new_y - self.y)
        self.x = new_x
        self.y = new_y

    def move_arms_toward(self, pose, rate):
        """Move both hands a fraction (rate, 0 to 1) of the way toward a pose."""
        (near_x, near_y), (far_x, far_y) = pose
        self.hand_near = (self.hand_near[0] + (near_x - self.hand_near[0]) * rate,
                          self.hand_near[1] + (near_y - self.hand_near[1]) * rate)
        self.hand_far = (self.hand_far[0] + (far_x - self.hand_far[0]) * rate,
                         self.hand_far[1] + (far_y - self.hand_far[1]) * rate)
        self.update_arms()

    def update_arms(self):
        """Redraw both arms and hands at their current positions."""
        c = self.canvas
        nx, ny = self.hand_near
        fx, fy = self.hand_far
        c.coords(self.arm_near, SHOULDER_NEAR[0], SHOULDER_NEAR[1], nx, ny)
        c.coords(self.arm_far, SHOULDER_FAR[0], SHOULDER_FAR[1], fx, fy)
        c.coords(self.palm_near, nx - 9, ny - 9, nx + 9, ny + 9)
        c.coords(self.palm_far, fx - 9, fy - 9, fx + 9, fy + 9)

    def show_explanation(self):
        messagebox.showinfo(
            "Why does the ball follow an arc?",
            "Horizontal velocity (vx) pushes the ball toward the hoop at a "
            "steady speed.\n\n"
            "Gravity changes the vertical velocity (vy) in every frame: "
            "vy = vy + gravity. The ball rises more slowly, stops at the top "
            "of the arc, then falls faster and faster.\n\n"
            "Sideways motion + changing vertical motion = a curved path "
            "(a parabola). With no gravity the ball would travel in a "
            "straight line.")

    # ------------------------------------------------------------------
    # The single animation loop and the state machine
    # ------------------------------------------------------------------
    def tick(self):
        """One animation frame. The ONLY place that calls after() for animation,
        so there is exactly one loop running at any time."""
        try:
            if self.state == DRIBBLING:
                self.update_dribbling()
            elif self.state == SHOOTING:
                self.update_shooting()
            elif self.state == RESETTING:
                self.update_resetting()
            elif self.state == RETURNING:
                self.update_returning()
            self.update_info_display()
        except Exception as error:      # show problems instead of freezing silently
            messagebox.showerror("Animation error", str(error))
            raise
        self.root.after(FRAME_DELAY_MS, self.tick)

    def request_shot(self):
        """Shoot button: ask for a shot at the next moment the ball is in the hand.
        It only sets a flag, so it can never start a second animation loop."""
        if self.state == DRIBBLING and not self.shoot_requested:
            self.shoot_requested = True
            self.show_message("Shot requested - shooting next catch!")

    # ---------------- DRIBBLING ----------------
    def update_dribbling(self):
        """The ball bounces between the hand and the floor."""
        self.vy = self.vy + self.gravity       # gravity speeds the ball up
        new_y = self.y + self.vy

        # Floor bounce: reverse direction with just enough speed to come back up
        if new_y >= FLOOR_Y - BALL_RADIUS and self.vy > 0:
            new_y = FLOOR_Y - BALL_RADIUS
            self.vy = -self.dribble_bounce_speed

        # The ball is rising and reaches the hand: the hand catches it
        if new_y <= BALL_START_Y and self.vy < 0:
            new_y = BALL_START_Y
            self.catch_count += 1
            if self.shoot_requested or self.catch_count >= DRIBBLES_BEFORE_SHOT:
                self.move_ball_to(BALL_START_X, new_y)
                self.begin_shot()
                return
            self.vy = DRIBBLE_PUSH_SPEED       # the hand pushes the ball down again

        self.move_ball_to(BALL_START_X, new_y)

        # The dribbling hand follows the ball (stays just above it)
        hand_y = max(POSE_REST[0][1], min(new_y - BALL_RADIUS - 4, 375))
        self.move_arms_toward(((BALL_START_X + 2, hand_y), POSE_REST[1]), 0.6)

    # ---------------- SHOOTING ----------------
    def begin_shot(self):
        """Switch from DRIBBLING to SHOOTING: the player holds the ball first."""
        self.state = SHOOTING
        self.hold_frames = HOLD_FRAMES
        self.manual_shot = self.shoot_requested
        self.shoot_requested = False
        self.vx = 0.0
        self.vy = 0.0
        self.show_message("Shooting!")

    def launch_ball(self):
        """Release the ball: turn power + angle into vx and vy."""
        self.scored_this_shot = False
        self.hit_rim = False
        self.frame_count = 0
        self.shots += 1
        self.update_score_display()
        self.canvas.delete("trail")            # remove the old arc dots

        angle = math.radians(self.angle_scale.get())
        power = float(self.power_scale.get())
        # Automatic shots vary a little so some score and some miss.
        # A shot requested with the button uses the sliders exactly.
        if self.vary_var.get() and not self.manual_shot:
            power += random.uniform(-POWER_VARIATION, POWER_VARIATION)
        self.vx = -power * math.cos(angle)     # negative = LEFT, toward the hoop
        self.vy = -power * math.sin(angle)     # negative = UP the screen
        self.show_message("")

    def update_shooting(self):
        if self.hold_frames > 0:
            # Player holds the ball with both hands, ready to shoot
            self.hold_frames -= 1
            self.move_arms_toward(POSE_SHOOT_HOLD, 0.4)
            if self.hold_frames == 0:
                self.launch_ball()
            return

        self.frame_count += 1
        previous_y = self.y

        # ---- projectile motion ----
        new_x = self.x + self.vx           # x = x + vx
        self.vy = self.vy + self.gravity   # vy = vy + gravity
        new_y = self.y + self.vy           # y = y + vy
        self.move_ball_to(new_x, new_y)

        # Leave a dot every 3 frames so the curved path is clearly visible
        if self.frame_count % 3 == 0:
            self.canvas.create_oval(self.x - 4, self.y - 4, self.x + 4, self.y + 4,
                                    fill="#f39c12", outline="", tags="trail")
            self.canvas.tag_raise("ball")

        # The shooting arm follows through (up and forward) after the release
        self.move_arms_toward(POSE_FOLLOW_THROUGH, 0.2)

        self.check_collisions(previous_y)

        if self.shot_is_over():
            self.end_shot()

    def check_collisions(self, previous_y):
        """Rim bounce and basket-entry detection."""
        # 1) Rim ends: if the ball hits the left or right end of the rim it
        #    bounces away once. Touching the rim never gives a point.
        if not self.hit_rim and not self.scored_this_shot:
            for rim_x in (RIM_LEFT_X, RIM_RIGHT_X):
                if math.hypot(self.x - rim_x, self.y - RIM_Y) < BALL_RADIUS * 0.5:
                    self.hit_rim = True
                    self.vx = -self.vx * 0.4
                    self.vy = -abs(self.vy) * 0.4
                    break

        # 2) Basket entry: the ball's centre must cross the rim line going
        #    DOWN while it is between the two ends of the rim.
        crossed_rim_downward = previous_y < RIM_Y <= self.y and self.vy > 0
        inside_opening = RIM_LEFT_X + 4 < self.x < RIM_RIGHT_X - 4
        if crossed_rim_downward and inside_opening and not self.scored_this_shot:
            self.scored_this_shot = True    # this flag stops a second point
            self.score += 1
            self.update_score_display()
            self.show_message("SCORE!  +1 point", "#1e8449")

        # After scoring, slow the sideways motion so the ball drops through the net
        if self.scored_this_shot:
            self.vx *= 0.6

    def shot_is_over(self):
        hit_floor = self.y >= FLOOR_Y - BALL_RADIUS
        off_screen = self.x < -50 or self.x > CANVAS_WIDTH + 50
        too_long = self.frame_count >= MAX_FRAMES
        return hit_floor or off_screen or too_long

    def end_shot(self):
        """The shot is finished: show the result and pause (RESETTING)."""
        if not self.scored_this_shot:
            self.show_message("Missed!", "#c0392b")
        # Put the ball on the floor (and on screen if it flew off the edge)
        self.move_ball_to(max(30, min(self.x, CANVAS_WIDTH - 30)),
                          FLOOR_Y - BALL_RADIUS)
        self.vx = 0.0
        self.vy = 0.0
        self.pause_frames = RESET_PAUSE_FRAMES
        self.state = RESETTING

    # ---------------- RESETTING ----------------
    def update_resetting(self):
        """Wait a moment so the result can be read; the arm returns to rest."""
        self.move_arms_toward(POSE_REST, 0.15)
        self.pause_frames -= 1
        if self.pause_frames <= 0:
            self.state = RETURNING
            self.vy = -6.0                     # first little hop
            self.show_message("Ball coming back...")

    # ---------------- RETURNING ----------------
    def update_returning(self):
        """The ball hops along the floor back to the player."""
        self.move_arms_toward(POSE_REST, 0.15)
        self.vx = RETURN_SPEED                 # positive = moving RIGHT
        self.vy = self.vy + self.gravity
        new_x = self.x + self.vx
        new_y = self.y + self.vy

        # Small bounces on the floor, getting lower but never stopping
        if new_y >= FLOOR_Y - BALL_RADIUS and self.vy > 0:
            new_y = FLOOR_Y - BALL_RADIUS
            self.vy = -max(abs(self.vy) * 0.6, 5.0)

        # The ball reaches the player: start dribbling again
        if new_x >= BALL_START_X:
            new_x = BALL_START_X
            self.vx = 0.0
            self.catch_count = 0
            self.state = DRIBBLING
            self.show_message("Dribbling...")

        self.move_ball_to(new_x, new_y)


def main():
    root = tk.Tk()
    BasketballGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()