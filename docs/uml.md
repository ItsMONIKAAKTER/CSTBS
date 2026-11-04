# CSTBS v5.2 — Access and Reservation UML (PlantUML)

## Administrator login use case

```plantuml
@startuml
left to right direction
actor Student
actor "Local server operator" as Operator
actor Administrator
rectangle CSTBS {
  usecase "Register with Student ID" as SR
  usecase "Login with student password" as SL
  usecase "Provision first admin (terminal)" as Setup
  usecase "Generate email-bound 20-minute key" as Key
  usecase "Login to Admin Dashboard" as AL
  usecase "Promote existing user" as Promote
  usecase "Manage events, seats and bookings" as Manage
  usecase "Reserve seats free of charge" as Book
}
Student --> SR
Student --> SL
Student --> Book
Operator --> Setup
Operator --> Key
Administrator --> AL
Administrator --> Promote
Administrator --> Manage
@enduml
```

## Login sequence

```plantuml
@startuml
actor "Local operator" as Operator
participant "run.py / admin-key CLI" as CLI
participant "Flask /admin/login" as Flask
participant "Flask-Login" as Session
participant "SQLite" as DB
actor Admin
Operator -> CLI : Enter admin email in terminal
CLI -> DB : Verify existing admin and store token HMAC
with target_user_id and 20-minute expiry
CLI --> Operator : Print one-time key once
Admin -> Flask : POST email, key and CSRF token
Flask -> DB : Validate email + keyed hash + expiry + target admin
Flask -> DB : Atomic consume used_at (single use)
DB --> Flask : Commit
Flask -> Session : login_user(admin, fresh=True)
Flask --> Admin : Redirect /admin/
@enduml
```

## Domain relationships

```plantuml
@startuml
class User { id; email; student_id; password_hash; role }
class AdminInvitation { id; token_hash; target_user_id; expires_at; used_at }
class Event { id; title; starts_at; venue; price }
class Seat { id; event_id; section; row_label; number; is_blocked }
class Booking { id; user_id; seat_id; status; price_at_booking }
User "1" <-- "*" AdminInvitation : target
User "1" <-- "*" Booking : owner
Event "1" <-- "*" Seat
Seat "1" <-- "*" Booking
note bottom of AdminInvitation : 20-minute one-time token.
HMAC fingerprint only.
@enduml
```

## Free seat reservation

```plantuml
@startuml
actor Student
participant "Seat map" as UI
participant "Flask Booking Routes" as API
database SQLite
Student -> UI : Select up to 6 seats
UI -> API : Review booking
API -> SQLite : Validate seat status
API --> Student : Free admission (CNY 0.00)
Student -> API : Confirm booking (CSRF)
API -> SQLite : Recheck availability; insert bookings
SQLite --> API : COMMIT or conflict
API --> Student : Confirmation / retry
@enduml
```
