# V5.4 stadium gates and check-in (PlantUML)

```plantuml
@startuml
class Event { id : integer; checkin_enabled : bool }
class Gate { id : integer; event_id : integer; name : string; is_open : bool }
class Seat { id : integer; event_id : integer; gate_id : integer; section : string; row_label : string; number : integer }
class Booking { id : integer; status : reserved|cancelled }
class Ticket { id : integer; status : active|checked_in|cancelled|unassigned; checked_in_gate_id : integer? }
class User { id : integer; student_id : string?; role : student|staff|admin }
Event "1" -- "many" Gate
Event "1" -- "many" Seat
Gate "1" -- "many" Seat : entrance
Seat "1" -- "many" Booking
Booking "1" -- "0..1" Ticket
User "1" -- "many" Ticket : attendee
Gate "0..1" -- "many" Ticket : entry logged at
@enduml
```

```plantuml
@startuml
actor "Gate Staff" as Staff
participant "Scan UI" as UI
participant "CSTBS Flask" as Server
database SQLite
Staff -> UI : choose event gate
Staff -> UI : scan QR camera / photograph
UI -> Server : GET verify signed ticket
Server -> SQLite : verify attendee, ticket, event and gate
SQLite --> Server : ticket + assigned gate + open states
Server --> UI : valid / waiting / invalid verdict
alt valid at correct open gate
  Staff -> Server : POST confirm entry + CSRF + gate ID
  Server -> SQLite : conditional UPDATE ticket.status=checked_in
  SQLite --> Server : rowcount=1 (or 0 if replay/closed)
  Server --> UI : entry approved / rejected
else event or gate closed
  Server --> UI : valid ticket - entry not open
end
@enduml
```


# CSTBS v5.3 — UML (PlantUML)

Use any PlantUML renderer to preview these diagrams. Code blocks can be pasted directly into a `.puml` file.

## 1. Domain class diagram

```plantuml
@startuml
skinparam classAttributeIconSize 0
class User {
  +id: int
  +email: string
  +student_id: string?
  +role: student|staff|admin
  +password_hash: string
  +password_ready: bool
  +auth_version: int
}
class AdminInvitation {
  +id: int
  +target_user_id: int
  +token_hash: string
  +expires_at: datetime
  +used_at: datetime?
}
class Event {
  +id: int
  +title: string
  +starts_at: datetime
  +booking_enabled: bool
  +checkin_enabled: bool
}
class Seat {
  +id: int
  +event_id: int
  +section: string
  +row_label: string
  +number: int
  +is_blocked: bool
}
class Booking {
  +id: int
  +user_id: int
  +seat_id: int
  +status: reserved|cancelled
}
class Ticket {
  +id: int
  +booking_id: int
  +attendee_user_id: int?
  +event_id: int
  +nonce: string
  +status: active|checked_in|cancelled|unassigned
  +checked_in_at: datetime?
}
User "1" -- "0..*" Booking : books
User "1" -- "0..*" Ticket : attends
User "1" -- "0..*" AdminInvitation : target
Event "1" -- "0..*" Seat
Event "1" -- "0..*" Ticket
Seat "1" -- "0..*" Booking
Booking "1" -- "0..1" Ticket
note right of Ticket
Unique event+attendee for live tickets;
QR signed with persistent key.
end note
@enduml
```

## 2. First admin activation and later sign-in

```plantuml
@startuml
actor "Trusted terminal operator" as Operator
actor Administrator as Admin
participant "CSTBS CLI" as CLI
participant "Flask /admin/activate" as Activation
participant "Flask /admin/login" as Login
participant "SQLite" as DB
Operator -> CLI : provision first admin / request key
CLI -> DB : issue HMAC-hashed key (20-minute expiry)
CLI --> Operator : display plaintext key once
Admin -> Activation : email + key + new password + CSRF
Activation -> DB : check target/expiry; consume once
Activation -> DB : store Werkzeug password hash; activate
Activation --> Admin : authenticated admin dashboard
... Later ...
Admin -> Login : email + password + CSRF
Login -> DB : compare password hash; check admin role
Login --> Admin : authenticated admin dashboard
@enduml
```

## 3. Group reservation and duplicate prevention

```plantuml
@startuml
actor Student
participant "Seat selection UI" as UI
participant "Booking routes" as Booking
participant "Attendee validation" as Validator
participant "SQLite" as DB
Student -> UI : select up to six free seats
UI -> Booking : POST review (CSRF)
Booking -> DB : check seats
Booking --> Student : attendee form per seat
Student -> Booking : names + Student IDs; confirm
Booking -> Validator : first must be buyer; others registered
Validator -> DB : verify exact IDs/names, active tickets
alt all eligible
  Booking -> DB : atomic insert bookings and Tickets
  note right of DB
  Partial indexes reject duplicate
  seat or attendee even under race.
  end note
  DB --> Booking : commit
  Booking --> Student : My tickets (QR per attendee)
else conflict
  Booking --> Student : reject; no partial booking
end
@enduml
```

## 4. QR verification and one-use stadium entry

```plantuml
@startuml
actor "Student attendee" as Student
actor "Authorized gate staff" as Staff
participant "Mobile QR scanner" as Camera
participant "GET /entry/verify/<token>" as Verify
participant "POST /entry/check-in/<token>" as CheckIn
database SQLite
Student -> Staff : present signed QR and student ID
Staff -> Camera : scan QR via camera / paste link
Camera -> Verify : GET signed token
Verify -> SQLite : check signature, nonce, ticket, booking, gate
Verify --> Staff : Valid / Used / Cancelled / Invalid / Gate Closed
alt Valid and identity matches
 Staff -> CheckIn : confirm POST (CSRF)
 CheckIn -> SQLite : conditional UPDATE only if active and reserved
 SQLite --> CheckIn : 1 updated / 0 updated
 CheckIn --> Staff : Checked in / rejected duplicate
end
@enduml
```

## 5. Deployment and backup boundary

```plantuml
@startuml
actor Developer
participant GitHub
participant "GitHub Actions" as CI
participant "Human reviewer" as Reviewer
participant "Staging server" as Staging
participant "Production server" as Production
database "Persistent SQLite" as DB
Developer -> GitHub : push branch / PR
GitHub -> CI : trigger tests + syntax checks
alt all tests pass
 CI --> Reviewer : green checks
 Reviewer -> Staging : approved release candidate
 Staging --> Reviewer : smoke and migration test results
 Reviewer -> Production : separate approved deployment
 Production -> DB : backup; explicit migration; health check
else tests fail
 CI --> Reviewer : failure; no deployment
end
note right of GitHub
Source repository never stores
secrets or production SQLite.
end note
@enduml
```
