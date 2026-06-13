// Tetris — browser-native, no deps. Renders to a canvas (the "video output"
// the agent watches) and takes controller inputs (LEFT/RIGHT/ROTATE/DOWN/DROP).
// state() exposes ground truth for the harness referee — the agent never reads
// this; it only sees the rendered frame.
(() => {
  const COLS = 10, ROWS = 20, CELL = 24;

  const PIECES = {
    I: { color: "#3CC7D6", cells: [[0, 0], [0, 1], [0, 2], [0, 3]] },
    O: { color: "#F2C94C", cells: [[0, 0], [0, 1], [1, 0], [1, 1]] },
    T: { color: "#A66BBE", cells: [[0, 1], [1, 0], [1, 1], [1, 2]] },
    S: { color: "#6FCF6F", cells: [[0, 1], [0, 2], [1, 0], [1, 1]] },
    Z: { color: "#EB5757", cells: [[0, 0], [0, 1], [1, 1], [1, 2]] },
    J: { color: "#5B8DEF", cells: [[0, 0], [1, 0], [1, 1], [1, 2]] },
    L: { color: "#F2994A", cells: [[0, 2], [1, 0], [1, 1], [1, 2]] },
  };
  const TYPES = Object.keys(PIECES);

  const emptyBoard = () =>
    Array.from({ length: ROWS }, () => Array(COLS).fill(null));
  const randType = () => TYPES[(Math.random() * TYPES.length) | 0];

  class Tetris {
    constructor() { this.reset(); }

    reset() {
      this.board = emptyBoard();
      this.score = 0;
      this.lines = 0;
      this.level = 1;
      this.frame = 0;
      this.flashRows = [];
      this.flashAt = 0;
      this.gameOver = false;
      this.nextType = randType();
      this._spawn();
    }

    _spawn() {
      const type = this.nextType;
      this.nextType = randType();
      const def = PIECES[type];
      this.cur = {
        type,
        color: def.color,
        cells: def.cells.map(([r, c]) => ({ r, c })),
        x: 3,
        y: 0,
      };
      if (this._collides(this.cur.cells, this.cur.x, this.cur.y)) {
        this.gameOver = true;
      }
    }

    _collides(cells, x, y) {
      for (const { r, c } of cells) {
        const R = y + r, C = x + c;
        if (C < 0 || C >= COLS || R >= ROWS) return true;
        if (R >= 0 && this.board[R][C]) return true;
      }
      return false;
    }

    _rotateCells(cells) {
      // CW: (r,c) -> (c,-r), then normalize to non-negative.
      const rot = cells.map(({ r, c }) => ({ r: c, c: -r }));
      const minR = Math.min(...rot.map((p) => p.r));
      const minC = Math.min(...rot.map((p) => p.c));
      return rot.map((p) => ({ r: p.r - minR, c: p.c - minC }));
    }

    input(btn) {
      if (this.gameOver) return;
      const cur = this.cur;
      if (btn === "LEFT" && !this._collides(cur.cells, cur.x - 1, cur.y)) cur.x--;
      else if (btn === "RIGHT" && !this._collides(cur.cells, cur.x + 1, cur.y)) cur.x++;
      else if (btn === "DOWN") {
        if (!this._collides(cur.cells, cur.x, cur.y + 1)) cur.y++;
        else this._lock();
      } else if (btn === "DROP") {
        while (!this._collides(cur.cells, cur.x, cur.y + 1)) cur.y++;
        this._lock();
      } else if (btn === "ROTATE") {
        const rc = this._rotateCells(cur.cells);
        for (const dx of [0, -1, 1, -2, 2]) {
          if (!this._collides(rc, cur.x + dx, cur.y)) {
            cur.cells = rc;
            cur.x += dx;
            break;
          }
        }
      }
    }

    tick() {
      if (this.gameOver) return;
      this.frame++;
      if (!this._collides(this.cur.cells, this.cur.x, this.cur.y + 1)) this.cur.y++;
      else this._lock();
    }

    _lock() {
      for (const { r, c } of this.cur.cells) {
        const R = this.cur.y + r, C = this.cur.x + c;
        if (R >= 0) this.board[R][C] = this.cur.color;
      }
      this._clearLines();
      this._spawn();
    }

    _clearLines() {
      // Capture the full rows (original indices) for the clear flash.
      const fullRows = [];
      for (let r = 0; r < ROWS; r++) if (this.board[r].every((c) => c)) fullRows.push(r);

      let cleared = 0;
      for (let r = ROWS - 1; r >= 0; r--) {
        if (this.board[r].every((c) => c)) {
          this.board.splice(r, 1);
          this.board.unshift(Array(COLS).fill(null));
          cleared++;
          r++; // recheck the row that shifted down into this index
        }
      }
      if (cleared) {
        this.score += [0, 100, 300, 500, 800][cleared] * this.level;
        this.lines += cleared;
        this.level = 1 + Math.floor(this.lines / 10);
        this.flashRows = fullRows; // brief white flash where the lines were
        this.flashAt = performance.now();
      }
    }

    _stackHeight() {
      for (let r = 0; r < ROWS; r++) {
        if (this.board[r].some((c) => c)) return ROWS - r;
      }
      return 0;
    }

    _holes() {
      let holes = 0;
      for (let c = 0; c < COLS; c++) {
        let seen = false;
        for (let r = 0; r < ROWS; r++) {
          if (this.board[r][c]) seen = true;
          else if (seen) holes++;
        }
      }
      return holes;
    }

    // Ground truth for the harness referee. The agent never reads this.
    state() {
      return {
        board: this.board.map((row) => row.map((c) => (c ? 1 : 0))),
        current: {
          type: this.cur.type,
          cells: this.cur.cells.map(({ r, c }) => [this.cur.y + r, this.cur.x + c]),
        },
        next: this.nextType,
        frame: this.frame,
        score: this.score,
        lines: this.lines,
        level: this.level,
        game_over: this.gameOver,
        stack_height: this._stackHeight(),
        holes: this._holes(),
      };
    }

    render(ctx) {
      ctx.fillStyle = "#0e0e0e";
      ctx.fillRect(0, 0, COLS * CELL, ROWS * CELL);
      for (let r = 0; r < ROWS; r++)
        for (let c = 0; c < COLS; c++)
          if (this.board[r][c]) drawCell(ctx, r, c, this.board[r][c]);
      if (!this.gameOver)
        for (const { r, c } of this.cur.cells)
          drawCell(ctx, this.cur.y + r, this.cur.x + c, this.cur.color);
      ctx.strokeStyle = "#1c1c1c";
      for (let c = 0; c <= COLS; c++) {
        ctx.beginPath();
        ctx.moveTo(c * CELL, 0);
        ctx.lineTo(c * CELL, ROWS * CELL);
        ctx.stroke();
      }
      for (let r = 0; r <= ROWS; r++) {
        ctx.beginPath();
        ctx.moveTo(0, r * CELL);
        ctx.lineTo(COLS * CELL, r * CELL);
        ctx.stroke();
      }
      // Line-clear flash: white bars fading out over ~160ms at the cleared rows.
      if (this.flashRows.length) {
        const t = (performance.now() - this.flashAt) / 160;
        if (t < 1) {
          ctx.fillStyle = `rgba(255,255,255,${0.85 * (1 - t)})`;
          for (const r of this.flashRows) ctx.fillRect(0, r * CELL, COLS * CELL, CELL);
        } else {
          this.flashRows = [];
        }
      }
      if (this.gameOver) {
        ctx.fillStyle = "rgba(0,0,0,.6)";
        ctx.fillRect(0, 0, COLS * CELL, ROWS * CELL);
        ctx.fillStyle = "#fff";
        ctx.font = "bold 22px -apple-system, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("GAME OVER", (COLS * CELL) / 2, (ROWS * CELL) / 2);
      }
    }
  }

  function drawCell(ctx, r, c, color) {
    if (r < 0) return;
    ctx.fillStyle = color;
    ctx.fillRect(c * CELL + 1, r * CELL + 1, CELL - 2, CELL - 2);
  }

  Tetris.COLS = COLS;
  Tetris.ROWS = ROWS;
  Tetris.CELL = CELL;
  window.Tetris = Tetris;
})();
