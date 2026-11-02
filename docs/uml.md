# CSTBS Version 3 — UML (PlantUML)

The following PlantUML source renders the main implemented V3 behavior; copy each block into any PlantUML viewer to generate diagrams.

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
rectangle "CSTBS v3" {
  usecase "Browse event catalog" as Browse
  usecase "Register / log in" as Auth
  usecase "View live seat availability" as Availability
  usecase "Select / review seats" as Review
  usecase "Confirm reservation" as Confirm
  usecase "View own booking history" as History
  usecase "Cancel own booking" as Cancel
  usecase "Manage events" as Manage
}
Visitor --> Browse
Visitor --> Auth
Visitor --> Availability
Student --> Review
Student --> Confirm
Student --> History
Student --> Cancel
Staff --> Review
Staff --> Confirm
Staff --> History
Staff --> Cancel
Admin --> Review
Admin --> Confirm
Admin --> History
Admin --> Cancel
Admin --> Manage
@enduml
```

## 2. Class/ER diagram

```plantuml
@startuml
hide methods
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
  +price: Numeric(10,2)
}
class Seat {
  +id: Integer
  +event_id: Integer <<FK>>
  +section: String
  +row_label: String
  +number: Integer
  +label: String
}
class Booking {
  +id: Integer
  +user_id: Integer <<FK>>
  +seat_id: Integer <<FK>>
  +status: reserved|cancelled
  +price_at_booking: Numeric(10,2)
  +created_at: DateTime
}
User "1" -- "0..*" Booking : owns
Event "1" -- "0..*" Seat : inventory
Seat "1" -- "0..*" Booking : history
note right of Booking
  SQLite partial UNIQUE index on seat_id
  when status = reserved.
end note
@enduml
```

## 3. Booking activity diagram

```plantuml
@startuml
start
:Sign in;
:Open event's seat map;
repeat
  :Select 1-6 available seats;
  :Poll availability every 5s;
repeat while (Want to change seats?) is (yes)
:Submit selection for review;
if (Seats belong to event and open?) then (yes)
  :Display reviewed seat list & total;
  :User confirms;
  :Recheck event and occupancy;
  if (Still available?) then (yes)
    :Insert all booking rows in transaction;
    if (Unique index permits COMMIT?) then (yes)
      :Display booking history;
    else (no)
      :Rollback all rows;
      :Return to seat map;
    endif
  else (no)
    :Return to seat map;
  endif
else (no)
  :Return to seat map with error;
endif
stop
@enduml
```

## 4. Seat availability / confirmation sequence

```plantuml
@startuml
actor Student
participant "Browser + seats.js" as Browser
participant "Flask routes" as Route
participant "SQLAlchemy" as ORM
database SQLite as DB
Student -> Browser : Select seats A1, A2
loop every 5 seconds
  Browser -> Route : GET /api/events/{id}/seats
  Route -> ORM : Load reserved seat IDs
  ORM -> DB : SELECT active bookings
  DB --> Browser : through API: JSON occupancy
end
Student -> Browser : Review seats
Browser -> Route : POST booking/review + CSRF
Route -> ORM : Validate selected seats
Route --> Browser : Review page; pending in session
Student -> Browser : Confirm
Browser -> Route : POST booking/confirm + CSRF
Route -> ORM : Revalidate + insert 2 bookings
ORM -> DB : COMMIT (unique partial index)
alt all seats remain available
  DB --> Route : Commit success
  Route --> Browser : Redirect /bookings
else somebody reserved a seat first
  DB --> Route : IntegrityError
  Route -> ORM : ROLLBACK
  Route --> Browser : Return to seat map; no partial booking
end
@enduml
```

## 5. Cancellation sequence

```plantuml
@startuml
actor Student
participant "Flask route" as Route
database SQLite as DB
Student -> Route : POST /bookings/{id}/cancel + CSRF
Route -> DB : SELECT booking WHERE user_id = current_user
alt own active booking
  Route -> DB : UPDATE status='cancelled'
  Route --> Student : Redirect /bookings; released seat
else other user's booking
  Route --> Student : 404 (no leaked details)
else already cancelled
  Route --> Student : Redirect /bookings; unchanged
end
@enduml
```
