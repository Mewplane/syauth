# Deterministic public signing fixture for the disposable NixOS guest.
import json, os
from pathlib import Path
import blake3
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
key = Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33)))
pub = key.public_key().public_bytes_raw()
peer = blake3.blake3(pub).digest()[:16].hex()
nonce = bytes.fromhex("a7" * 16)
signature = key.sign(b"\x01" + nonce).hex()
root = Path('/var/lib/syauth')
(root / 'keys').mkdir(exist_ok=True, mode=0o700)
(root / 'bonds.toml').write_text(f'''schema_version = 1
[[bond]]
peer_id = "{peer}"
pubkey = "{pub.hex()}"
name = "vm-synthetic-phone"
created_at = "1970-01-01T00:00:00Z"
[bond.status]
kind = "Bonded"
''')
(root / 'keys' / (peer + '.bin')).write_bytes(bytes([0xcc]) * 32)
for path in [root / 'keys', root / 'bonds.toml', root / 'keys' / (peer + '.bin')]:
    os.chown(path, 1100, 100)
    os.chmod(path, 0o700 if path.is_dir() else 0o600)
Path('/root/fixture.json').write_text(json.dumps(dict(peer=peer, nonce=nonce.hex(), signature=signature)))
