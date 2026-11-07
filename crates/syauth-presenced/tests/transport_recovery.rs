//! Exercise controller removal through the real daemon and a private BlueZ bus.
use std::{
    collections::HashMap,
    io::{BufRead, BufReader},
    process::{Child, Command, Stdio},
    sync::{
        Arc,
        atomic::{AtomicU8, Ordering},
    },
    time::Duration,
};

use syauth_core::{Bond, BondStatus, BondStore, peer_id_from_pubkey};
use syauth_presenced::{Request, Response, read_frame, write_frame};
use zbus::zvariant::{OwnedObjectPath, OwnedValue};

type Options = HashMap<String, OwnedValue>;

#[derive(Default)]
struct Adapter {
    powered: bool,
    discoverable: bool,
    pairable: bool,
}
#[zbus::interface(name = "org.bluez.Adapter1")]
impl Adapter {
    #[zbus(property)]
    fn powered(&self) -> bool {
        self.powered
    }
    #[zbus(property)]
    fn set_powered(&mut self, value: bool) {
        self.powered = value;
    }
    #[zbus(property)]
    fn discoverable(&self) -> bool {
        self.discoverable
    }
    #[zbus(property)]
    fn set_discoverable(&mut self, value: bool) {
        self.discoverable = value;
    }
    #[zbus(property)]
    fn pairable(&self) -> bool {
        self.pairable
    }
    #[zbus(property)]
    fn set_pairable(&mut self, value: bool) {
        self.pairable = value;
    }
}
struct Advertising(Arc<AtomicU8>);
#[zbus::interface(name = "org.bluez.LEAdvertisingManager1")]
impl Advertising {
    fn register_advertisement(&self, _path: OwnedObjectPath, _options: Options) {
        self.0.store(1, Ordering::SeqCst);
    }
    fn unregister_advertisement(&self, _path: OwnedObjectPath) {
        self.0.store(0, Ordering::SeqCst);
    }
    #[zbus(property)]
    fn active_instances(&self) -> u8 {
        self.0.load(Ordering::SeqCst)
    }
}
struct Gatt;
#[zbus::interface(name = "org.bluez.GattManager1")]
impl Gatt {
    fn register_application(&self, _path: OwnedObjectPath, _options: Options) {}
    fn unregister_application(&self, _path: OwnedObjectPath) {}
}
struct Agent;
#[zbus::interface(name = "org.bluez.AgentManager1")]
impl Agent {
    fn register_agent(&self, _path: OwnedObjectPath, _capability: String) {}
    fn request_default_agent(&self, _path: OwnedObjectPath) {}
    fn unregister_agent(&self, _path: OwnedObjectPath) {}
}

struct Process(Child);
impl Drop for Process {
    fn drop(&mut self) {
        let _ = self.0.kill();
        let _ = self.0.wait();
    }
}

async fn add_adapter(bus: &zbus::Connection, name: &str) -> Arc<AtomicU8> {
    let path = format!("/org/bluez/{name}");
    let active = Arc::new(AtomicU8::new(0));
    bus.object_server().at(path.as_str(), Adapter::default()).await.expect("adapter");
    bus.object_server()
        .at(path.as_str(), Advertising(active.clone()))
        .await
        .expect("advertising");
    bus.object_server().at(path.as_str(), Gatt).await.expect("GATT");
    active
}

async fn status(socket: &std::path::Path) -> Option<Response> {
    let mut stream = tokio::net::UnixStream::connect(socket).await.ok()?;
    write_frame(&mut stream, &Request::Status).await.ok()?;
    read_frame(&mut stream).await.ok()
}

#[tokio::test]
async fn removed_controller_exits_and_relaunch_advertises_on_replacement() {
    let root = tempfile::tempdir().expect("tempdir");
    use std::os::unix::fs::PermissionsExt;
    std::fs::set_permissions(root.path(), std::fs::Permissions::from_mode(0o700)).expect("private bond directory");
    let pubkey = [0xAC; 32];
    let peer_id = peer_id_from_pubkey(&pubkey);
    let mut bonds = BondStore::empty();
    bonds
        .add(Bond {
            peer_id: peer_id.clone(),
            pubkey,
            name: "phone".into(),
            created_at: time::OffsetDateTime::UNIX_EPOCH,
            status: BondStatus::Bonded,
        })
        .expect("bond");
    let bonds_file = root.path().join("bonds.toml");
    bonds.save(&bonds_file).expect("save bond");
    let original_bonds = std::fs::read(&bonds_file).expect("original bond bytes");
    std::fs::create_dir(root.path().join("keys")).expect("keys dir");
    let key_path = root.path().join("keys").join(format!("{peer_id}.bin"));
    std::fs::write(&key_path, [0xAB; 32]).expect("key");
    let mut broker = Process(
        Command::new("dbus-daemon")
            .args(["--session", "--nofork", "--print-address=1"])
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .spawn()
            .expect("private D-Bus"),
    );
    let mut address = String::new();
    BufReader::new(broker.0.stdout.take().expect("bus address"))
        .read_line(&mut address)
        .expect("read address");
    let bus = zbus::connection::Builder::address(address.trim())
        .expect("bus builder")
        .name("org.bluez")
        .expect("name")
        .serve_at("/", zbus::fdo::ObjectManager)
        .expect("objects")
        .serve_at("/org/bluez", Agent)
        .expect("agent")
        .build()
        .await
        .expect("bus");
    let active = add_adapter(&bus, "hci0").await;
    let socket = root.path().join("auth.sock");
    let spawn = || {
        Process(
            Command::new(env!("CARGO_BIN_EXE_syauth-presenced"))
                .arg("--socket")
                .arg(&socket)
                .arg("--pidfile")
                .arg(root.path().join("pid"))
                .arg("--bonds-file")
                .arg(root.path().join("bonds.toml"))
                .arg("--keys-dir")
                .arg(root.path().join("keys"))
                .arg("--audit-log")
                .arg(root.path().join("audit.log"))
                .env("DBUS_SYSTEM_BUS_ADDRESS", address.trim())
                .stdout(Stdio::null())
                .stderr(Stdio::piped())
                .spawn()
                .expect("daemon"),
        )
    };
    let mut daemon = spawn();
    tokio::time::timeout(Duration::from_secs(5), async {
        loop {
            if matches!(
                status(&socket).await,
                Some(Response::Status {
                    transport_ready: Some(true),
                    ..
                })
            ) {
                break;
            }
            if let Some(code) = daemon.0.try_wait().expect("wait") {
                let output = daemon.0.stderr.take().expect("stderr");
                let log = std::io::read_to_string(output).expect("log");
                panic!("daemon exited {code}: {log}");
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
    })
    .await
    .expect("initial advertising");
    assert_eq!(active.load(Ordering::SeqCst), 1);
    bus.object_server()
        .remove::<Adapter, _>("/org/bluez/hci0")
        .await
        .expect("remove controller");
    bus.object_server()
        .remove::<Advertising, _>("/org/bluez/hci0")
        .await
        .expect("remove advertising");
    bus.object_server().remove::<Gatt, _>("/org/bluez/hci0").await.expect("remove GATT");
    let replacement = add_adapter(&bus, "hci1").await;
    let code = tokio::time::timeout(Duration::from_secs(5), async {
        loop {
            if let Some(code) = daemon.0.try_wait().expect("wait") {
                break code;
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
    })
    .await
    .expect("transport failure exits for systemd restart");
    assert!(!code.success());
    assert!(!socket.exists(), "failed daemon cleans its RPC socket");
    let _replacement_daemon = spawn();
    tokio::time::timeout(Duration::from_secs(5), async {
        loop {
            if matches!(
                status(&socket).await,
                Some(Response::Status {
                    transport_ready: Some(true),
                    ..
                })
            ) {
                break;
            }
            tokio::time::sleep(Duration::from_millis(20)).await;
        }
    })
    .await
    .expect("replacement controller advertises");
    assert_eq!(replacement.load(Ordering::SeqCst), 1);
    let Some(Response::Status { peers, .. }) = status(&socket).await else {
        panic!("replacement status")
    };
    assert_eq!(peers[0].peer_id, peer_id, "recovery hydrates the existing bond");
    assert_eq!(std::fs::read(bonds_file).expect("bond"), original_bonds);
    assert_eq!(std::fs::read(key_path).expect("key"), [0xAB; 32]);
}
