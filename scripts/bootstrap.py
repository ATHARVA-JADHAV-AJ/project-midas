"""
Project Midas — Bootstrap Script
Author: Atharva Kishor Jadhav (AJ)
---------------------------------------------------------------
Run once before first launch to:
  1. Generate the .env file with a fresh JWT_SECRET and DISPATCHER_SECRET
  2. Prompt the operator for at least one admin user and write users.json
  3. Create the outputs/ directory

Known limitation: users.json is a plaintext file. Anyone with host filesystem
access can edit it directly. This is a deliberate prototype-scope simplification.
Production hardening should replace users.json with an encrypted credential store.

Usage:
    python scripts/bootstrap.py
"""

import os
import json
import secrets
import hashlib
from pathlib import Path
from getpass import getpass
import bcrypt

ROOT = Path(__file__).resolve().parent.parent


def generate_env():
    env_path = ROOT / ".env"
    if env_path.exists():
        overwrite = input(".env already exists. Overwrite secrets? [y/N]: ").strip().lower()
        if overwrite != "y":
            print("Skipping .env generation.")
            return

    jwt_secret = secrets.token_hex(32)
    dispatcher_secret = secrets.token_hex(32)

    # Read existing .env template and fill in the generated secrets
    template_path = ROOT / ".env"
    env_text = template_path.read_text() if template_path.exists() else ""

    env_text = env_text.replace("REPLACE_ME_WITH_A_STRONG_SECRET", jwt_secret)
    env_text = env_text.replace("REPLACE_ME_WITH_DISPATCHER_SECRET", dispatcher_secret)
    env_path.write_text(env_text)
    print(f"[OK] .env updated with fresh secrets.")


def create_users():
    users_path = ROOT / "users.json"

    existing = {}
    if users_path.exists():
        with open(users_path) as f:
            existing = json.load(f)

    print("\nAdd admin user (required):")
    username = input("  Username: ").strip()
    if not username:
        print("[ERROR] Username cannot be empty. Aborting.")
        return

    password = getpass("  Password: ")
    confirm = getpass("  Confirm password: ")
    if password != confirm:
        print("[ERROR] Passwords do not match. Aborting.")
        return

    existing[username] = {
        "hashed_password": bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
        "role": "admin",
    }

    while True:
        add_more = input("\nAdd another user? [y/N]: ").strip().lower()
        if add_more != "y":
            break
        uname = input("  Username: ").strip()
        role = input("  Role (admin/analyst/default): ").strip()
        if role not in ("admin", "analyst", "default"):
            print("  Invalid role. Skipping.")
            continue
        pw = getpass("  Password: ")
        existing[uname] = {
            "hashed_password": bcrypt.hashpw(pw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            "role": "admin" if role == "admin" else role,
        }

    with open(users_path, "w") as f:
        json.dump(existing, f, indent=2)
    print(f"[OK] users.json written with {len(existing)} user(s).")


def create_dirs():
    for d in ["outputs", "logs"]:
        (ROOT / d).mkdir(exist_ok=True)
    # Seed the dispatch log so the volume mount always finds the file
    dispatch_log = ROOT / "tier_b_dispatch.log"
    if not dispatch_log.exists():
        dispatch_log.touch()
    print("[OK] Directory structure ready.")


if __name__ == "__main__":
    print("=" * 60)
    print("  Project Midas — Bootstrap")
    print("  Author: Atharva Kishor Jadhav (AJ)")
    print("=" * 60)
    generate_env()
    create_users()
    create_dirs()
    print("\n[DONE] Bootstrap complete. Run: docker compose up --build")
