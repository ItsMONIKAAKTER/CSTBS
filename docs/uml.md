# CSTBS Version 4 — UML (PlantUML)

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
