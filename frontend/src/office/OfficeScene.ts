import Phaser from 'phaser';

export interface AgentVisualData {
  id: string;
  name: string;
  role: string;
  dept: string;
  x: number;
  y: number;
  facing: 'front' | 'back';
  meetX: number;
  meetY: number;
  breakX: number;
  breakY: number;
  state: string;
}

interface AgentEntity {
  data: AgentVisualData;
  folder: string;
  sprite: Phaser.GameObjects.Sprite;
  ring: Phaser.GameObjects.Sprite;
  statusIcon: Phaser.GameObjects.Sprite;
  nameTag: Phaser.GameObjects.Text;
  isMoving: boolean;
  tween?: Phaser.Tweens.Tween;
}

const ANIM_ROWS = [
  'idle_down', 'idle_up', 'idle_left', 'idle_right',
  'walk_down', 'walk_up', 'walk_left', 'walk_right',
  'sit_back', 'sit_front', 'talk', 'celebrate', 'read'
] as const;

const PROP_PATHS: Record<string, string> = {
  // Desks
  desk_wood: 'furniture/desks/desk_wood.png',
  desk_white: 'furniture/desks/desk_white.png',
  desk_dark: 'furniture/desks/desk_dark.png',
  desk_exec: 'furniture/desks/desk_exec.png',
  desk_lamp: 'furniture/desks/desk_lamp.png',
  desk_mic: 'furniture/desks/desk_mic.png',
  reception_desk: 'furniture/desks/reception_desk.png',
  conference_table: 'furniture/desks/conference_table.png',
  coffee_table: 'furniture/desks/coffee_table.png',
  kitchen_counter: 'furniture/desks/kitchen_counter.png',
  bench_table: 'furniture/desks/bench_table.png',
  // Chairs & Sofas
  chair_back: 'furniture/chairs/chair_back.png',
  chair_back_red: 'furniture/chairs/chair_back_red.png',
  chair_front: 'furniture/chairs/chair_front.png',
  chair_front_wine: 'furniture/chairs/chair_front_wine.png',
  chair_exec: 'furniture/chairs/chair_exec.png',
  sofa_teal: 'furniture/chairs/sofa_teal.png',
  sofa_wine: 'furniture/chairs/sofa_wine.png',
  sofa_orange: 'furniture/chairs/sofa_orange.png',
  armchair_red: 'furniture/chairs/armchair_red.png',
  armchair_blue: 'furniture/chairs/armchair_blue.png',
  beanbag_yellow: 'furniture/chairs/beanbag_yellow.png',
  beanbag_pink: 'furniture/chairs/beanbag_pink.png',
  // Computers & Tech
  mon_code: 'furniture/computers/mon_code.png',
  mon_dual_code: 'furniture/computers/mon_dual_code.png',
  mon_dual_chart: 'furniture/computers/mon_dual_chart.png',
  mon_dual_dash: 'furniture/computers/mon_dual_dash.png',
  mon_dual_test: 'furniture/computers/mon_dual_test.png',
  mon_news: 'furniture/computers/mon_news.png',
  mon_script: 'furniture/computers/mon_script.png',
  mon_wave: 'furniture/computers/mon_wave.png',
  mon_subs: 'furniture/computers/mon_subs.png',
  mon_timeline: 'furniture/computers/mon_timeline.png',
  mon_design: 'furniture/computers/mon_design.png',
  mon_back: 'furniture/computers/mon_back.png',
  laptop: 'furniture/computers/laptop.png',
  keyboard: 'furniture/computers/keyboard.png',
  monitoring_wall: 'furniture/computers/monitoring_wall.png',
  printer: 'furniture/computers/printer.png',
  projector: 'furniture/computers/projector.png',
  // Shelves
  bookshelf: 'furniture/shelves/bookshelf.png',
  bookshelf_tall: 'furniture/shelves/bookshelf_tall.png',
  filing_cabinet: 'furniture/shelves/filing_cabinet.png',
  // Servers
  server_rack_a: 'furniture/servers/server_rack_a.png',
  server_rack_b: 'furniture/servers/server_rack_b.png',
  server_rack_c: 'furniture/servers/server_rack_c.png',
  network_cabinet: 'furniture/servers/network_cabinet.png',
  ups_unit: 'furniture/servers/ups_unit.png',
  cable_run: 'furniture/servers/cable_run.png',
  // Plants
  plant_monstera: 'environment/plants/plant_monstera.png',
  plant_snake: 'environment/plants/plant_snake.png',
  plant_tree: 'environment/plants/plant_tree.png',
  plant_small: 'environment/plants/plant_small.png',
  plant_cactus: 'environment/plants/plant_cactus.png',
  // Windows & Lighting
  window: 'environment/windows/window.png',
  floor_lamp: 'environment/lighting/floor_lamp.png',
  softbox: 'environment/lighting/softbox.png',
  ring_light: 'environment/lighting/ring_light.png',
  // Decorations
  whiteboard_kanban: 'furniture/decorations/whiteboard_kanban.png',
  whiteboard_plan: 'furniture/decorations/whiteboard_plan.png',
  tv_graph: 'furniture/decorations/tv_graph.png',
  tv_dash: 'furniture/decorations/tv_dash.png',
  painting_landscape: 'furniture/decorations/painting_landscape.png',
  painting_abstract: 'furniture/decorations/painting_abstract.png',
  painting_chart: 'furniture/decorations/painting_chart.png',
  empire_crest: 'furniture/decorations/empire_crest.png',
  wall_clock: 'furniture/decorations/wall_clock.png',
  acoustic_panel: 'furniture/decorations/acoustic_panel.png',
  neon_sign: 'furniture/decorations/neon_sign.png',
  cork_board: 'furniture/decorations/cork_board.png',
  logo_wall: 'furniture/decorations/logo_wall.png',
  water_cooler: 'furniture/decorations/water_cooler.png',
  vending_machine: 'furniture/decorations/vending_machine.png',
  fridge: 'furniture/decorations/fridge.png',
  trash_bin: 'furniture/decorations/trash_bin.png',
  mic_stand: 'furniture/decorations/mic_stand.png',
  headphones: 'furniture/decorations/headphones.png',
  mixer: 'furniture/decorations/mixer.png',
  drawing_tablet: 'furniture/decorations/drawing_tablet.png',
  camera_tripod: 'furniture/decorations/camera_tripod.png',
  green_screen: 'furniture/decorations/green_screen.png',
  arcade: 'furniture/decorations/arcade.png',
  foosball: 'furniture/decorations/foosball.png',
  rug_red: 'furniture/decorations/rug_red.png',
  rug_blue_round: 'furniture/decorations/rug_blue_round.png',
  rug_green: 'furniture/decorations/rug_green.png',
  rug_purple: 'furniture/decorations/rug_purple.png',
  rug_beige: 'furniture/decorations/rug_beige.png',
  coffee_mug: 'furniture/decorations/coffee_mug.png',
  paper_stack: 'furniture/decorations/paper_stack.png',
};

const WALL_TEXTURES = [
  'wall_exterior', 'wall_beige', 'wall_wood', 'wall_acoustic',
  'wall_teal', 'wall_brick', 'wall_gray',
  'partition_glass', 'wall_cap_v', 'wall_cap_v_end', 'wall_cap_h',
];

const DOOR_TEXTURES = ['door_wood', 'door_metal', 'door_dark', 'entrance_doors', 'welcome_mat'];

export class OfficeScene extends Phaser.Scene {
  private onAgentClick?: (agentId: string) => void;
  private onAgentHover?: (agent: AgentVisualData | null, screenX: number, screenY: number) => void;
  private onSceneReady?: () => void;

  private mapCols = 58;
  private mapRows = 38;
  private tileSize = 32;
  private mapWidth = 58 * 32;
  private mapHeight = 38 * 32;

  private collisionGrid: number[][] = [];
  private roomsData: any[] = [];
  private agents: Map<string, AgentEntity> = new Map();
  private selectedAgentId: string | null = null;
  private pendingStates: Record<string, string> = {};

  private isDragging = false;
  private dragMoved = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private pinchStartDist = 0;
  private pinchStartZoom = 1;

  constructor() {
    super({ key: 'OfficeScene' });
  }

  public setAgentClickHandler(fn: (agentId: string) => void) {
    this.onAgentClick = fn;
  }

  public setAgentHoverHandler(fn: (agent: AgentVisualData | null, screenX: number, screenY: number) => void) {
    this.onAgentHover = fn;
  }

  public setSceneReadyHandler(fn: () => void) {
    this.onSceneReady = fn;
  }

  preload() {
    this.load.json('office_map', '/sprites/maps/office_map.json');
    this.load.image('office_floors_img', '/sprites/tilesets/office_floors.png');

    WALL_TEXTURES.forEach((t) => {
      this.load.image(t, `/sprites/environment/walls/${t}.png`);
    });

    DOOR_TEXTURES.forEach((t) => {
      this.load.image(t, `/sprites/environment/doors/${t}.png`);
    });

    Object.entries(PROP_PATHS).forEach(([key, rel]) => {
      this.load.image(key, `/sprites/${rel}`);
    });

    ['selection_ring', 'speech_bubble', 'status_alert', 'status_sparkle', 'status_coding'].forEach((fx) => {
      this.load.image(fx, `/sprites/effects/${fx}.png`);
    });

    const folders = [
      'jeffrey', 'fonseca', 'balsini', 'jarvis', 'noe', 'ford', 'murphy',
      'script-agent', 'news-agent', 'voice-agent', 'subtitle-agent',
      'clipador-agent', 'designer-agent', 'video-agent'
    ];
    folders.forEach((folder) => {
      this.load.spritesheet(`agent_${folder}`, `/sprites/agents/${folder}/spritesheet.png`, {
        frameWidth: 32,
        frameHeight: 48,
      });
    });
  }

  create() {
    const mapJson = this.cache.json.get('office_map');
    if (!mapJson) return;

    this.mapCols = mapJson.width;
    this.mapRows = mapJson.height;
    this.tileSize = mapJson.tilewidth;
    this.mapWidth = this.mapCols * this.tileSize;
    this.mapHeight = this.mapRows * this.tileSize;

    // 1. Floor Tilemap Layer
    const floorLayerData = mapJson.layers.find((l: any) => l.name === 'floor');
    const colLayerData = mapJson.layers.find((l: any) => l.name === 'collision');

    const tilemap = this.make.tilemap({
      tileWidth: this.tileSize,
      tileHeight: this.tileSize,
      width: this.mapCols,
      height: this.mapRows,
    });
    const tileset = tilemap.addTilesetImage('office_floors', 'office_floors_img', 32, 32, 0, 0);
    if (tileset && floorLayerData) {
      const layer = tilemap.createBlankLayer('floor', tileset);
      if (layer) {
        layer.setDepth(0);
        for (let r = 0; r < this.mapRows; r++) {
          for (let c = 0; c < this.mapCols; c++) {
            const gid = floorLayerData.data[r * this.mapCols + c];
            if (gid > 0) {
              layer.putTileAt(gid - 1, c, r);
            }
          }
        }
      }
    }

    // 2. Collision grid
    this.collisionGrid = [];
    for (let r = 0; r < this.mapRows; r++) {
      this.collisionGrid[r] = [];
      for (let c = 0; c < this.mapCols; c++) {
        this.collisionGrid[r][c] = colLayerData ? colLayerData.data[r * this.mapCols + c] : 0;
      }
    }

    // 3. Rugs
    const custom = mapJson.custom || {};
    (custom.rugs || []).forEach((rug: any) => {
      this.add.image(rug.x, rug.y, rug.texture).setDepth(2);
    });

    // 4. Walls & Partitions
    (custom.walls || []).forEach((w: any) => {
      const img = this.add.image(w.x, w.y, w.texture);
      // Tall wall faces anchor at bottom so they sit cleanly on the tile
      if (w.texture.startsWith('wall_') && w.texture !== 'wall_cap_v' && w.texture !== 'wall_cap_h') {
        img.setOrigin(0.5, 1);
      } else if (w.texture === 'partition_glass' || w.texture === 'wall_cap_v_end' || w.texture.startsWith('door_')) {
        img.setOrigin(0.5, 1);
      }
      img.setDepth(w.depth);
    });

    // 5. Furniture & Props
    (custom.props || []).forEach((p: any) => {
      const img = this.add.image(p.x, p.y, p.texture);
      img.setDepth(p.depth);
    });

    // 6. Subtle architectural room plaques
    this.roomsData = custom.rooms || [];
    this.roomsData.forEach((rm) => {
      this.createRoomPlaque(rm.labelX, rm.labelY, rm.name, rm.color);
    });

    // 7. Register agent animations & spawn all 14 agents
    this.registerAgentAnimations();
    (custom.agents || []).forEach((a: any, idx: number) => {
      this.spawnAgent({ ...a, state: this.pendingStates[a.id] || 'Idle' }, idx);
    });

    // 8. Camera & Controls
    this.setupCamera();
    this.setupControls();
    this.startAmbientEffects();

    if (this.onSceneReady) {
      this.onSceneReady();
    }
  }

  private createRoomPlaque(x: number, y: number, label: string, colorHex: string) {
    const colorNum = Phaser.Display.Color.HexStringToColor(colorHex).color;
    const txt = this.add.text(x, y, label, {
      fontFamily: 'monospace',
      fontSize: '10px',
      color: '#f8fafc',
      fontStyle: 'bold',
    }).setOrigin(0.5).setDepth(9900);

    const bg = this.add.graphics().setDepth(9899);
    const padX = 7;
    const w = txt.width + padX * 2;
    const h = 15;
    bg.fillStyle(0x0f172a, 0.82);
    bg.lineStyle(1, colorNum, 0.9);
    bg.fillRoundedRect(x - w / 2, y - h / 2, w, h, 3);
    bg.strokeRoundedRect(x - w / 2, y - h / 2, w, h, 3);
  }

  private registerAgentAnimations() {
    const folders = [
      'jeffrey', 'fonseca', 'balsini', 'jarvis', 'noe', 'ford', 'murphy',
      'script-agent', 'news-agent', 'voice-agent', 'subtitle-agent',
      'clipador-agent', 'designer-agent', 'video-agent'
    ];
    folders.forEach((folder) => {
      const texKey = `agent_${folder}`;
      ANIM_ROWS.forEach((animName, rowIdx) => {
        const key = `${folder}_${animName}`;
        if (this.anims.exists(key)) return;
        const fps = animName.startsWith('walk') ? 7 : animName === 'celebrate' ? 6 : 3;
        this.anims.create({
          key,
          frames: this.anims.generateFrameNumbers(texKey, {
            start: rowIdx * 4,
            end: rowIdx * 4 + 3,
          }),
          frameRate: fps,
          repeat: -1,
        });
      });
    });
  }

  private spawnAgent(a: AgentVisualData, index: number) {
    const folder = a.id.replace('_', '-');

    const ring = this.add.sprite(a.x, a.y, 'selection_ring')
      .setDepth(a.y - 1)
      .setVisible(false);

    const sprite = this.add.sprite(a.x, a.y, `agent_${folder}`, 0)
      .setOrigin(0.5, 0.94)
      .setDepth(a.y)
      .setInteractive({ useHandCursor: true });

    const statusIcon = this.add.sprite(a.x, a.y - 52, 'status_coding')
      .setDepth(a.y + 5)
      .setVisible(false);

    const tagOffsetY = a.facing === 'back' ? 12 : 6;
    const nameTag = this.add.text(a.x, a.y + tagOffsetY, a.name, {
      fontFamily: 'monospace',
      fontSize: '9px',
      color: '#e2e8f0',
      backgroundColor: '#0f172acc',
      padding: { x: 4, y: 1 },
    }).setOrigin(0.5, 0).setDepth(a.y + 4);

    // Stagger animation phase so 14 characters don't move identically
    this.time.delayedCall((index * 170) % 900, () => {
      if (sprite.scene) {
        this.applyStateVisual(a.id, a.state);
      }
    });

    sprite.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      pointer.event.stopPropagation();
      this.selectAgent(a.id);
    });

    sprite.on('pointerover', (pointer: Phaser.Input.Pointer) => {
      nameTag.setColor('#38bdf8');
      if (this.onAgentHover) {
        this.onAgentHover(a, pointer.x, pointer.y);
      }
    });

    sprite.on('pointerout', () => {
      nameTag.setColor('#e2e8f0');
      if (this.onAgentHover) {
        this.onAgentHover(null, 0, 0);
      }
    });

    this.agents.set(a.id, {
      data: a,
      folder,
      sprite,
      ring,
      statusIcon,
      nameTag,
      isMoving: false,
    });
  }

  public setInitialAgentStates(apiAgents: { id: string; operational_state?: string }[]) {
    apiAgents.forEach((a) => {
      const state = a.operational_state || 'idle';
      this.pendingStates[a.id] = state;
      if (this.agents.has(a.id)) {
        this.updateAgentVisualState(a.id, state);
      }
    });
  }

  public updateAgentVisualState(agentId: string, rawState: string) {
    this.pendingStates[agentId] = rawState;
    const ent = this.agents.get(agentId);
    if (!ent) return;
    ent.data.state = rawState;
    if (!ent.isMoving) {
      this.applyStateVisual(agentId, rawState);
    }
  }

  private applyStateVisual(agentId: string, rawState: string) {
    const ent = this.agents.get(agentId);
    if (!ent) return;

    const s = rawState.toLowerCase();
    const sitAnim = ent.data.facing === 'front' ? `${ent.folder}_sit_front` : `${ent.folder}_sit_back`;
    const idleAnim = ent.data.facing === 'front' ? `${ent.folder}_idle_down` : `${ent.folder}_idle_up`;

    if (s === 'coding' || s === 'working' || s === 'creating') {
      ent.sprite.play(sitAnim, true);
      ent.statusIcon.setTexture('status_coding').setVisible(true);
    } else if (s === 'planning' || s === 'researching' || s === 'reviewing') {
      ent.sprite.play(`${ent.folder}_read`, true);
      ent.statusIcon.setTexture('speech_bubble').setVisible(false);
    } else if (s === 'communicating') {
      ent.sprite.play(`${ent.folder}_talk`, true);
      ent.statusIcon.setTexture('speech_bubble').setVisible(true);
    } else if (s === 'completed') {
      ent.sprite.play(`${ent.folder}_celebrate`, true);
      ent.statusIcon.setTexture('status_sparkle').setVisible(true);
      this.time.delayedCall(5000, () => {
        if (ent.data.state.toLowerCase() === 'completed') {
          this.updateAgentVisualState(agentId, 'Idle');
        }
      });
    } else if (s === 'blocked' || s === 'error') {
      ent.sprite.play(`${ent.folder}_idle_down`, true);
      ent.statusIcon.setTexture('status_alert').setVisible(true);
    } else if (s === 'waiting') {
      ent.sprite.play(`${ent.folder}_idle_down`, true);
      ent.statusIcon.setTexture('speech_bubble').setVisible(true);
    } else {
      ent.sprite.play(idleAnim, true);
      ent.statusIcon.setVisible(false);
    }
  }

  public selectAgent(agentId: string) {
    if (this.selectedAgentId && this.agents.has(this.selectedAgentId)) {
      this.agents.get(this.selectedAgentId)!.ring.setVisible(false);
    }
    this.selectedAgentId = agentId;
    const ent = this.agents.get(agentId);
    if (!ent) return;

    ent.ring.setVisible(true);
    this.cameras.main.pan(ent.sprite.x, ent.sprite.y - 16, 450, 'Cubic.easeInOut', true);
    if (this.cameras.main.zoom < 1.15) {
      this.cameras.main.zoomTo(1.25, 450, 'Cubic.easeInOut', true);
    }

    if (this.onAgentClick) {
      this.onAgentClick(agentId);
    }
  }

  // -----------------------------------------------------------
  // A* Pathfinding & Movement
  // -----------------------------------------------------------
  public moveAgentTo(agentId: string, targetX: number, targetY: number, onArrival?: () => void) {
    const ent = this.agents.get(agentId);
    if (!ent) return;
    if (ent.tween) {
      ent.tween.stop();
      ent.tween = undefined;
    }

    const sc = Math.floor(ent.sprite.x / this.tileSize);
    const sr = Math.floor(ent.sprite.y / this.tileSize);
    const tc = Math.floor(targetX / this.tileSize);
    const tr = Math.floor(targetY / this.tileSize);

    const path = this.findPathAStar(sc, sr, tc, tr);
    const waypoints = path.length > 0
      ? path.map((p, idx) =>
          idx === path.length - 1
            ? { x: targetX, y: targetY }
            : { x: p.c * this.tileSize + 16, y: p.r * this.tileSize + 16 }
        )
      : [{ x: targetX, y: targetY }];

    this.followWaypoints(ent, waypoints, 0, onArrival);
  }

  private followWaypoints(
    ent: AgentEntity,
    waypoints: { x: number; y: number }[],
    idx: number,
    onArrival?: () => void
  ) {
    if (idx >= waypoints.length) {
      ent.isMoving = false;
      this.applyStateVisual(ent.data.id, ent.data.state);
      if (onArrival) onArrival();
      return;
    }

    ent.isMoving = true;
    const wp = waypoints[idx];
    const dx = wp.x - ent.sprite.x;
    const dy = wp.y - ent.sprite.y;

    if (Math.abs(dx) > Math.abs(dy)) {
      ent.sprite.play(dx >= 0 ? `${ent.folder}_walk_right` : `${ent.folder}_walk_left`, true);
    } else {
      ent.sprite.play(dy >= 0 ? `${ent.folder}_walk_down` : `${ent.folder}_walk_up`, true);
    }

    const dist = Phaser.Math.Distance.Between(ent.sprite.x, ent.sprite.y, wp.x, wp.y);
    const duration = Math.max(80, (dist / 135) * 1000);

    ent.tween = this.tweens.add({
      targets: ent.sprite,
      x: wp.x,
      y: wp.y,
      duration,
      onUpdate: () => {
        ent.sprite.setDepth(ent.sprite.y);
        ent.ring.setPosition(ent.sprite.x, ent.sprite.y).setDepth(ent.sprite.y - 1);
        ent.statusIcon.setPosition(ent.sprite.x, ent.sprite.y - 52).setDepth(ent.sprite.y + 5);
        const tagOffsetY = ent.data.facing === 'back' ? 12 : 6;
        ent.nameTag.setPosition(ent.sprite.x, ent.sprite.y + tagOffsetY).setDepth(ent.sprite.y + 4);
      },
      onComplete: () => this.followWaypoints(ent, waypoints, idx + 1, onArrival),
    });
  }

  private findPathAStar(sc: number, sr: number, tc: number, tr: number): { c: number; r: number }[] {
    const key = (c: number, r: number) => `${c},${r}`;
    const h = (c: number, r: number) => Math.abs(c - tc) + Math.abs(r - tr);

    const open: { c: number; r: number; g: number; f: number }[] = [{ c: sc, r: sr, g: 0, f: h(sc, sr) }];
    const cameFrom = new Map<string, { c: number; r: number }>();
    const gScore = new Map<string, number>([[key(sc, sr), 0]]);
    const closed = new Set<string>();

    const dirs = [
      { dc: 0, dr: 1 }, { dc: 0, dr: -1 },
      { dc: 1, dr: 0 }, { dc: -1, dr: 0 },
    ];

    let iterations = 0;
    while (open.length > 0 && iterations < 4000) {
      iterations++;
      open.sort((a, b) => a.f - b.f);
      const curr = open.shift()!;
      const ck = key(curr.c, curr.r);

      if (curr.c === tc && curr.r === tr) {
        const result: { c: number; r: number }[] = [];
        let trace: { c: number; r: number } | undefined = { c: tc, r: tr };
        while (trace && !(trace.c === sc && trace.r === sr)) {
          result.unshift(trace);
          trace = cameFrom.get(key(trace.c, trace.r));
        }
        return result;
      }

      closed.add(ck);

      for (const d of dirs) {
        const nc = curr.c + d.dc;
        const nr = curr.r + d.dr;
        if (nc < 0 || nc >= this.mapCols || nr < 0 || nr >= this.mapRows) continue;
        const nk = key(nc, nr);
        if (closed.has(nk)) continue;

        const isGoal = nc === tc && nr === tr;
        if (!isGoal && this.collisionGrid[nr]?.[nc] === 1) continue;

        const tentativeG = curr.g + 1;
        if (tentativeG < (gScore.get(nk) ?? Infinity)) {
          cameFrom.set(nk, { c: curr.c, r: curr.r });
          gScore.set(nk, tentativeG);
          const f = tentativeG + h(nc, nr);
          const existing = open.find((n) => n.c === nc && n.r === nr);
          if (existing) {
            existing.g = tentativeG;
            existing.f = f;
          } else {
            open.push({ c: nc, r: nr, g: tentativeG, f });
          }
        }
      }
    }
    return [];
  }

  // -----------------------------------------------------------
  // Collaborative Swarm / Meeting / Break Actions
  // -----------------------------------------------------------
  public summonAllHandsMeeting() {
    this.agents.forEach((ent, id) => {
      this.moveAgentTo(id, ent.data.meetX, ent.data.meetY, () => {
        ent.sprite.play(`${ent.folder}_talk`, true);
        ent.statusIcon.setTexture('speech_bubble').setVisible(true);
      });
    });
    this.focusOnRoom('meeting');
  }

  public dismissToDesks() {
    this.agents.forEach((ent, id) => {
      this.moveAgentTo(id, ent.data.x, ent.data.y, () => {
        this.applyStateVisual(id, ent.data.state);
      });
    });
  }

  public focusOnRoom(roomId: string) {
    if (roomId === 'all') {
      this.resetCamera();
      return;
    }
    const rm = this.roomsData.find((r) => r.id === roomId);
    if (!rm) return;
    this.cameras.main.pan(rm.x, rm.y, 450, 'Cubic.easeInOut', true);
    this.cameras.main.zoomTo(rm.zoom || 1.25, 450, 'Cubic.easeInOut', true);
  }

  public zoomIn() {
    const next = Math.min(2.4, this.cameras.main.zoom + 0.2);
    this.cameras.main.zoomTo(next, 200, 'Sine.easeOut', true);
  }

  public zoomOut() {
    const next = Math.max(0.45, this.cameras.main.zoom - 0.2);
    this.cameras.main.zoomTo(next, 200, 'Sine.easeOut', true);
  }

  public resetCamera() {
    const fitZoom = Math.min(
      this.cameras.main.width / this.mapWidth,
      this.cameras.main.height / this.mapHeight
    );
    const targetZoom = Phaser.Math.Clamp(Math.max(fitZoom, 0.72), 0.5, 1.2);
    this.cameras.main.pan(this.mapWidth / 2, this.mapHeight / 2, 450, 'Cubic.easeInOut', true);
    this.cameras.main.zoomTo(targetZoom, 450, 'Cubic.easeInOut', true);
  }

  // -----------------------------------------------------------
  // Camera & Input (Desktop + Mobile Pinch/Drag)
  // -----------------------------------------------------------
  private setupCamera() {
    this.cameras.main.setBounds(0, 0, this.mapWidth, this.mapHeight);
    this.cameras.main.setRoundPixels(true);
    const fitZoom = Math.min(
      this.cameras.main.width / this.mapWidth,
      this.cameras.main.height / this.mapHeight
    );
    this.cameras.main.setZoom(Phaser.Math.Clamp(Math.max(fitZoom, 0.72), 0.5, 1.2));
    this.cameras.main.centerOn(this.mapWidth / 2, this.mapHeight / 2);

    this.scale.on('resize', (gameSize: Phaser.Structs.Size) => {
      if (gameSize.width > 0 && gameSize.height > 0 && this.cameras?.main) {
        this.cameras.main.setSize(gameSize.width, gameSize.height);
      }
    });
  }

  private setupControls() {
    this.input.addPointer(1); // Support 2 simultaneous pointers for pinch-to-zoom

    this.input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      const p1 = this.input.pointer1;
      const p2 = this.input.pointer2;
      if (p1.isDown && p2.isDown) {
        this.isDragging = false;
        this.pinchStartDist = Phaser.Math.Distance.Between(p1.x, p1.y, p2.x, p2.y);
        this.pinchStartZoom = this.cameras.main.zoom;
        return;
      }
      this.isDragging = true;
      this.dragMoved = false;
      this.dragStartX = pointer.x;
      this.dragStartY = pointer.y;
    });

    this.input.on('pointermove', (pointer: Phaser.Input.Pointer) => {
      const p1 = this.input.pointer1;
      const p2 = this.input.pointer2;
      if (p1.isDown && p2.isDown && this.pinchStartDist > 0) {
        const dist = Phaser.Math.Distance.Between(p1.x, p1.y, p2.x, p2.y);
        const newZoom = Phaser.Math.Clamp(this.pinchStartZoom * (dist / this.pinchStartDist), 0.45, 2.4);
        this.cameras.main.setZoom(newZoom);
        return;
      }
      if (this.isDragging && pointer.isDown) {
        const dx = pointer.x - this.dragStartX;
        const dy = pointer.y - this.dragStartY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
          this.dragMoved = true;
        }
        this.cameras.main.scrollX -= dx / this.cameras.main.zoom;
        this.cameras.main.scrollY -= dy / this.cameras.main.zoom;
        this.dragStartX = pointer.x;
        this.dragStartY = pointer.y;
      }
    });

    this.input.on('pointerup', () => {
      this.isDragging = false;
      this.pinchStartDist = 0;
    });

    this.input.on('wheel', (_p: any, _g: any, _dx: number, deltaY: number) => {
      const cur = this.cameras.main.zoom;
      const next = deltaY > 0 ? Math.max(0.45, cur - 0.12) : Math.min(2.4, cur + 0.12);
      this.cameras.main.setZoom(next);
    });
  }

  private startAmbientEffects() {
    // Subtle blinking LED glow over the server racks in Infrastructure room
    const ledOverlay = this.add.graphics().setDepth(5 * 32 + 10);
    const rackXs = [42, 44, 46, 50, 52];
    this.time.addEvent({
      delay: 750,
      loop: true,
      callback: () => {
        ledOverlay.clear();
        rackXs.forEach((rc) => {
          const lx = rc * 32 + 6 + Phaser.Math.Between(0, 10);
          const ly = 5 * 32 - 14 + Phaser.Math.Between(0, 26);
          const col = Phaser.Math.RND.pick([0x4ade80, 0x38bdf8, 0xfacc15]);
          ledOverlay.fillStyle(col, 0.9);
          ledOverlay.fillRect(lx, ly, 2, 2);
        });
      },
    });
  }
}
