"""Promote an existing registered account to STAFF from the trusted local CLI only."""
import argparse

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Student, UserAccount


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote an existing SIS account to STAFF")
    parser.add_argument("--email", required=True, help="Email of the already-registered account")
    args = parser.parse_args()
    with SessionLocal() as db:
        account = db.scalar(
            select(UserAccount).join(Student).where(Student.email == args.email.lower().strip())
        )
        if account is None:
            parser.error("No registered account exists for that email")
        account.role = "STAFF"
        db.commit()
        print(f"Promoted account id={account.id} to STAFF. Log in again to receive a STAFF token.")


if __name__ == "__main__":
    main()
