use std::any::type_name;
use std::env;
use std::fs::{self, OpenOptions};
use std::io::{self, Write};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{SystemTime, UNIX_EPOCH};

use mod_api::*;

const MOD_ID: &str = "tfm2_lol_anchor_probe";
const EVIDENCE_ENV: &str = "TFM2_RUNTIME_NODE_ANCHOR_EVIDENCE_DIR";

static WROTE_EVIDENCE: AtomicBool = AtomicBool::new(false);

#[derive(Debug)]
struct RuntimeNodeAnchorProbeExtension;

impl ModExtension for RuntimeNodeAnchorProbeExtension {
    fn post_update(&self, _scene: &mut Scene, _ui: &mut GameUI, _assets: &mut Assets, dt: f32) {
        if WROTE_EVIDENCE.load(Ordering::SeqCst) {
            return;
        }
        if write_runtime_evidence(dt).is_ok() {
            WROTE_EVIDENCE.store(true, Ordering::SeqCst);
        }
    }
}

fn init(_ctx: &GameCtx) -> ModRegistration {
    let mut reg = ModRegistration::new(MOD_ID);
    reg.set_extension(RuntimeNodeAnchorProbeExtension);
    reg
}

declare_mod!(init);

fn evidence_dir() -> PathBuf {
    if let Ok(path) = env::var(EVIDENCE_ENV) {
        if !path.trim().is_empty() {
            return PathBuf::from(path);
        }
    }

    let current_dir = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    let installed_config = current_dir
        .join("mods")
        .join(MOD_ID)
        .join("probe_evidence_dir.txt");
    if let Ok(path) = fs::read_to_string(installed_config) {
        let trimmed = path.trim();
        if !trimmed.is_empty() {
            return PathBuf::from(trimmed);
        }
    }

    current_dir
        .join("stage_runtime_node_anchor_evidence")
        .join("runtime_node_anchor_probe")
}

fn unix_timestamp() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_secs())
        .unwrap_or(0)
}

fn json_escape(value: &str) -> String {
    value
        .replace('\\', "\\\\")
        .replace('"', "\\\"")
        .replace('\n', "\\n")
        .replace('\r', "\\r")
}

fn write_runtime_evidence(dt: f32) -> io::Result<()> {
    let dir = evidence_dir();
    fs::create_dir_all(&dir)?;

    let json = format!(
        concat!(
            "{{\n",
            "  \"probe\": \"runtime_node_anchor_read_only\",\n",
            "  \"mod_id\": \"{}\",\n",
            "  \"timestamp_unix\": {},\n",
            "  \"first_dt\": {},\n",
            "  \"post_update_called\": true,\n",
            "  \"scene_type\": \"{}\",\n",
            "  \"game_ui_type\": \"{}\",\n",
            "  \"assets_type\": \"{}\",\n",
            "  \"map_setting_override_installed\": false,\n",
            "  \"asset_overrides_installed\": false,\n",
            "  \"scene_mutated\": false,\n",
            "  \"anchor_surface\": \"post_update_only_no_public_anchor_fields\",\n",
            "  \"anchors\": [],\n",
            "  \"candidate_transform\": null,\n",
            "  \"map_setting_node_world_transform\": \"unproven\"\n",
            "}}\n"
        ),
        MOD_ID,
        unix_timestamp(),
        dt,
        json_escape(type_name::<Scene>()),
        json_escape(type_name::<GameUI>()),
        json_escape(type_name::<Assets>())
    );
    fs::write(dir.join("runtime_node_anchor.json"), json)?;

    let mut log = OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir.join("runtime_node_anchor.log"))?;
    writeln!(
        log,
        "runtime_node_anchor_probe: post_update observed; no public anchor fields accessed"
    )?;
    Ok(())
}
