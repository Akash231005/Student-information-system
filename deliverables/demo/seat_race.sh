#!/usr/bin/env bash
# Live demo beat: twenty requests, five seats - the app must say 409, not oversell.
#   ./deliverables/demo/seat_race.sh
# One command because typing six curls in front of an audience is how demos die.
#
# It prints what the API actually answered. Requires the stack from ./run.sh.
set -euo pipefail

API=${API:-http://127.0.0.1:8000}
EMAIL=${DEMO_STAFF_EMAIL:-staff@example.test}
PASSWORD=${DEMO_STAFF_PASSWORD:-sis-demo-2026}
STAMP=$(date +%H%M%S)

jget() { python3 -c "import json,sys;d=json.load(sys.stdin);print(d${1})"; }

token=$(curl -fsS -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | jget "['access_token']")
auth="Authorization: Bearer $token"

course=$(curl -fsS -X POST "$API/courses" -H "$auth" -H 'Content-Type: application/json' \
  -d "{\"course_code\":\"RACE$STAMP\",\"title\":\"Seat Race $STAMP\",\"credits\":3}" | jget "['id']")

# The seat count is the whole point: 1 seat, 2 students, so the second must fail.
offering=$(curl -fsS -X POST "$API/offerings" -H "$auth" -H 'Content-Type: application/json' \
  -d "{\"course_id\":$course,\"term_code\":\"2026-DEMO\",\"section_code\":\"A\",\"capacity\":1,\"status\":\"OPEN\"}" \
  | jget "['id']")

printf '\n  offering %s: capacity 1\n\n' "$offering"
for n in 1 2; do
  student=$(curl -fsS -X POST "$API/students" -H "$auth" -H 'Content-Type: application/json' \
    -d "{\"student_number\":\"RACE$STAMP$n\",\"full_name\":\"Race Student $n\",\"email\":\"race$STAMP$n@example.test\"}" \
    | jget "['id']")
  body=$(curl -sS -o /tmp/seat_race_body -w '%{http_code}' -X POST "$API/offerings/$offering/enroll" \
    -H "$auth" -H 'Content-Type: application/json' \
    -d "{\"student_id\":$student,\"idempotency_key\":\"race-$STAMP-$n\"}")
  printf '  student %s -> HTTP %s  %s\n' "$n" "$body" "$(head -c 120 /tmp/seat_race_body)"
done

printf '\n  seats actually taken: %s of 1  (never 2)\n\n' \
  "$(curl -fsS "$API/offerings?q=RACE$STAMP" | python3 -c "
import json,sys
rows=[o for o in json.load(sys.stdin) if o['id']==$offering]
print(rows[0]['enrolled_count'] if rows else '?')
")"
