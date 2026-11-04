# CSTBS v5.1 — University Registration UML

## Student and administrator registration use cases

```plantuml
@startuml
left to right direction
actor Student
actor "First local operator" as Operator
actor Administrator
rectangle "CSTBS v5.1" {
  usecase "Register with Student ID" as StudentReg
  usecase "Generate bootstrap key in terminal" as Bootstrap
  usecase "Register with one-time admin key" as AdminReg
  usecase "Issue new admin key from dashboard" as Issue
  usecase "Manage Student IDs and roles" as Manage
  usecase "Reserve university seats for free" as Booking
}
Student --> StudentReg
Student --> Booking
Operator --> Bootstrap
Administrator --> AdminReg
Administrator --> Issue
Administrator --> Manage
@enduml
```

## Domain additions

```plantuml
@startuml
class User {
 +id: Integer
 +email: String
 +student_id: String [unique, nullable legacy]
 +role: student|staff|admin
}
class AdminInvitation {
 +id: Integer
 +token_hash: String [unique]
 +bootstrap: Boolean
 +created_at: DateTime
 +expires_at: DateTime
 +used_at: DateTime?
 +created_by_id: Integer?
 +used_by_id: Integer?
}
User "1" <-- "0..*" AdminInvitation : created_by
User "1" <-- "0..*" AdminInvitation : used_by
note right of AdminInvitation
 HMAC-SHA256; no raw token stored
 60-minute TTL; atomic one-use update
end note
@enduml
```

## Administrator invitation sequence

```plantuml
@startuml
actor Admin
participant "Admin web UI" as Web
participant "Flask admin" as API
database SQLite
actor "Invited admin" as NewAdmin
Admin -> Web : Generate one-time key
Web -> API : POST /admin/admin-invitations/new + CSRF
API -> SQLite : INSERT invitation HMAC hash + expiry
SQLite --> API : committed
API --> Web : Show plaintext key once (no-store)
Admin -> NewAdmin : Share key privately
NewAdmin -> API : POST /register/admin + key + form + CSRF
API -> SQLite : Look up valid hashed key
API -> SQLite : INSERT user; guarded UPDATE used_at
SQLite --> API : COMMIT; account created
API --> NewAdmin : Admin dashboard
@enduml
```

## Booking without payment

```plantuml
@startuml
actor Student
participant "Seat map" as Web
participant "Booking routes" as Flask
database SQLite
Student -> Web : Choose seats
Web -> Flask : Review selected seats
Flask -> SQLite : Check blocked/reserved status
Flask --> Web : Free admission, ¥0.00
Student -> Flask : Confirm (CSRF)
Flask -> SQLite : Recheck + insert bookings (price_at_booking=0)
SQLite --> Flask : Commit / conflict
Flask --> Student : Booking confirmation / error
@enduml
```

---

## V5 UML (historical context)

# CSTBS Version 5 — UML (PlantUML)

The original V4 diagrams are preserved below; V5 adds reporting and export sequence diagrams.

The following diagrams describe the implemented V4 architecture. Paste any code block into a PlantUML renderer.

## 1. Use-case diagram

```plantuml
@startuml
left to right direction
actor Visitor
actor Student
actor Staff
actor Admin
Visitor <|-- Student
Visitor <|-- Staff
Visitor <|-- Admin
rectangle "CSTBS v4" {
  usecase "Browse events" as Browse
  usecase "Register / login" as Auth
  usecase "Choose / confirm seats" as Reserve
  usecase "View / cancel own bookings" as My
  usecase "Admin dashboard" as Dash
  usecase "Manage events" as Events
  usecase "Manage seat blocks & sections" as Seats
  usecase "Promote / demote users" as Roles
  usecase "Browse / cancel all bookings" as Bookings
  usecase "Notify owner by email" as Email
}
Visitor --> Browse
Visitor --> Auth
Student --> Reserve
Student --> My
Staff --> Reserve
Staff --> My
Admin --> Reserve
Admin --> My
Admin --> Dash
Admin --> Events
Admin --> Seats
Admin --> Roles
Admin --> Bookings
Reserve .> Email : <<include>>
My .> Email : <<include>>
Bookings .> Email : <<include>>
@enduml
```

## 2. Domain class diagram

```plantuml
@startuml
skinparam classAttributeIconSize 0
class User {
  +id: Integer
  +email: String <<unique>>
  +full_name: String
  +password_hash: String
  +role: student|staff|admin
  +created_at: DateTime
}
class Event {
  +id: Integer
  +title: String
  +category: String
  +description: Text
  +venue: String
  +starts_at: DateTime
  +price: Decimal
}
class Seat {
  +id: Integer
  +event_id: Integer
  +section: String
  +row_label: String
  +number: Integer
  +is_blocked: Boolean <<V4>>
  +display_label: String
}
class Booking {
  +id: Integer
  +user_id: Integer
  +seat_id: Integer
  +status: reserved|cancelled
  +price_at_booking: Decimal
  +created_at: DateTime
}
class NotificationService {
  +notify_booking_confirmed(user, event, bookings)
  +notify_booking_cancelled(booking)
}
User "1" -- "0..*" Booking : owns
Event "1" -- "0..*" Seat : seats
Seat "1" -- "0..*" Booking : history
NotificationService ..> Booking : after commit
note right of Seat
  Section is a string attribute.
  DB triggers prohibit active
  bookings on blocked seats.
end note
note bottom of Booking
  Unique partial index seat_id
  WHERE status = reserved.
end note
@enduml
```

## 3. Administrator seat/block sequence

```plantuml
@startuml
actor Admin
participant "Browser" as Browser
participant "Flask admin routes" as AdminRoutes
database "SQLite" as DB
Admin -> Browser : Open /admin/events/{id}/seats
Browser -> AdminRoutes : GET seat inventory
AdminRoutes -> DB : SELECT seats + active bookings
DB --> AdminRoutes : Rows + booked IDs
AdminRoutes --> Browser : Render sections and seat controls
Admin -> Browser : Block available seat
Browser -> AdminRoutes : POST /admin/seats/{id}/toggle-block + CSRF
AdminRoutes -> DB : Verify not reserved; UPDATE is_blocked=1
alt booking raced in
  DB --> AdminRoutes : trigger IntegrityError
  AdminRoutes --> Browser : Flash conflict; seat unchanged
else success
  DB --> AdminRoutes : commit
  AdminRoutes --> Browser : Flash blocked
end
@enduml
```

## 4. Booking confirmation with email notification

```plantuml
@startuml
actor Student
participant "Flask routes" as Routes
database SQLite as DB
participant "Notification service" as Notify
participant "Flask-Mail / console" as Mail
Student -> Routes : POST booking/confirm + CSRF
Routes -> DB : Recheck event, seats, occupancy, blocks
Routes -> DB : INSERT booking rows; COMMIT
alt constraint violation (reserved or blocked)
  DB --> Routes : IntegrityError
  Routes -> DB : ROLLBACK all seat rows
  Routes --> Student : Retry seat map; no email
else commit succeeds
  DB --> Routes : Saved booking IDs
  Routes -> Notify : notify_booking_confirmed(...)
  Notify -> Mail : Console preview or SMTP send
  alt delivery fails
    Mail --> Notify : Exception
    Notify --> Routes : Log failure; keep committed records
  end
  Routes --> Student : Redirect /bookings
end
@enduml
```

## 5. Admin cancellation and owner notification

```plantuml
@startuml
actor Admin
participant "Admin bookings route" as Route
database SQLite as DB
participant "Notifications" as Mail
Admin -> Route : POST /admin/bookings/{id}/cancel + CSRF
Route -> DB : Lookup booking
alt status = reserved
  Route -> DB : UPDATE status=cancelled; COMMIT
  Route -> Mail : Email booking owner
  Route --> Admin : Redirect + success message
else already cancelled
  Route --> Admin : No change; no repeated email
end
@enduml
```

## 6. Components overview

```plantuml
@startuml
package "Flask app" {
  [main routes: catalog/auth/booking] as Main
  [admin blueprint: dashboard/roles/inventory/bookings] as Admin
  [authz: admin_required] as Authz
  [notifications: Flask-Mail] as Notif
  [SQLAlchemy models] as Models
  [SQLite compatibility upgrades] as Migrate
}
database "SQLite / instance/cstbs.db" as Database
cloud "Console or Ethereal SMTP" as Smtp
Main --> Models
Admin --> Authz
Admin --> Models
Main --> Notif
Admin --> Notif
Notif --> Smtp
Models --> Database
Migrate --> Database
@enduml
```


## 5. V5 reporting use case

```plantuml
@startuml
left to right direction
actor Admin
rectangle "CSTBS Version 5" {
  usecase "Open reporting center" as Center
  usecase "Filter booking data" as Filter
  usecase "Export booking PDF" as BPDF
  usecase "Export booking CSV" as BCSV
  usecase "Export event PDF" as EPDF
  usecase "Export event CSV" as ECSV
}
Admin --> Center
Admin --> Filter
Admin --> BPDF
Admin --> BCSV
Admin --> EPDF
Admin --> ECSV
Filter .> BPDF : <<extend>>
Filter .> BCSV : <<extend>>
note bottom of Center
All report actions require authenticated
admin role; no public report access.
end note
@enduml
```

## 6. V5 report export sequence

```plantuml
@startuml
actor Admin
participant "Browser" as Browser
participant "Flask report blueprint" as Report
participant "Role authorization" as Auth
participant "SQLAlchemy" as ORM
database SQLite as DB
participant "ReportLab / CSV writer" as Output
Admin -> Browser : Click Download (format, filters)
Browser -> Report : GET /admin/reports/bookings.pdf?status=reserved
Report -> Auth : login_required + admin_required
alt user not admin
  Auth --> Report : Redirect login or 403
  Report --> Browser : No export
else admin
  Report -> Report : Validate filter & maximum rows
  Report -> ORM : SELECT filtered booking records
  ORM -> DB : SQL query
  DB --> ORM : Rows
  ORM --> Report : Bookings + relationships
  Report -> Output : Render in memory
  Output --> Report : BytesIO PDF/CSV
  Report --> Browser : Attachment + Cache-Control: no-store
end
@enduml
```

## 7. Component structure

```plantuml
@startuml
package "CSTBS Flask" {
  [Main Blueprint] as Main
  [Admin Blueprint] as Admin
  [Reports Blueprint] as Reports
  [Forms + CSRF] as Forms
  [Flask-Login + roles] as Auth
  [Flask-Limiter] as Limiter
  [SQLAlchemy models] as ORM
  [Flask-Mail] as Mail
  [ReportLab + CSV] as Render
}
database "SQLite" as DB
Main --> Forms
Admin --> Auth
Reports --> Auth
Main --> Limiter
Reports --> ORM
Reports --> Render
Admin --> ORM
Main --> ORM
ORM --> DB
Main --> Mail
@enduml
```
