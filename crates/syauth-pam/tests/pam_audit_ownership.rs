//! BUG-20261108-audit-ownership: root-run PAM must not lock out daemon auditing.

use std::{
    fs,
    os::unix::fs::{MetadataExt as _, chown},
};

use pam_syauth::{auth::authenticate, config::Config};

const STORE_UID: u32 = 65534;
const STORE_GID: u32 = 65534;

// Run explicitly as root against a tempdir; no host PAM stack is accessed.
#[test]
#[ignore = "requires root; run in an isolated container or the CI tempdir test step"]
fn pam_first_log_is_owned_by_store_account() {
    assert!(nix::unistd::geteuid().is_root(), "run this test as root");
    let store = tempfile::tempdir().expect("store");
    chown(store.path(), Some(STORE_UID), Some(STORE_GID)).expect("store owner");
    let config = Config::for_tests(store.path());
    assert!(!authenticate(&config).is_success());
    let log = config.last_log_path();
    let metadata = fs::metadata(&log).expect("PAM created log");
    assert_eq!((metadata.uid(), metadata.gid()), (STORE_UID, STORE_GID));
    assert_eq!(metadata.mode() & 0o777, 0o600);
    let first = fs::read_to_string(&log).expect("first record");
    assert!(!authenticate(&config).is_success());
    assert!(fs::read_to_string(&log).expect("second record").starts_with(&first));
    assert_eq!(fs::read_to_string(&log).expect("records").lines().count(), 2);
}
