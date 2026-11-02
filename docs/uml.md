# CSTBS Version 1 — UML Diagrams

All diagrams below use [PlantUML](https://plantuml.com/) syntax. Paste the code into any PlantUML renderer to generate a diagram. Dashed interactions show **UI-only** behavior and do not imply real account or booking workflows.

## 1. Use case diagram

Visitor can browse event data and inspect prototype account forms. There is **no booking use case in V1**.

```plantuml
@startuml
left to right direction
actor Visitor
rectangle "CSTBS V1" {
  usecase "View homepage" as UC1
  usecase "Browse events" as UC2
  usecase "View event details" as UC3
  usecase "Preview login form" as UC4
  usecase "Preview registration form" as UC5
}
Visitor --> UC1
Visitor --> UC2
Visitor --> UC3
Visitor --> UC4
Visitor --> UC5
@enduml
```

## 2. Class diagram (initial schema)

`Booking` belongs to a `User` and a `Seat`; the associated event is obtained through `Seat.event_id`. `Seat` is unique within an event by `(section, row_label, number)`.

```plantuml
@startuml
hide methods
skinparam classAttributeIconSize 0
class User {
  +id: Integer
  +full_name: String
  +email: String [unique]
  +password_hash: String
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
  +event_id: Integer [FK]
  +section: String
  +row_label: String
  +number: Integer
}
class Booking {
  +id: Integer
  +user_id: Integer [FK]
  +seat_id: Integer [FK]
  +status: String
  +created_at: DateTime
}
Event "1" -- "0..*" Seat : contains
Seat "1" -- "0..*" Booking : referenced by
User "1" -- "0..*" Booking : makes
@enduml
```

## 3. Component diagram

The route/controller layer reads event records, renders Jinja2 templates, and validates prototype forms with Flask-WTF. SQLAlchemy is the persistence boundary.

```plantuml
@startuml
skinparam componentStyle rectangle
actor Visitor
component "Flask Routes" as Routes
component "Jinja2 Templates" as Templates
component "Flask-WTF Forms" as Forms
component "SQLAlchemy Models" as Models
database "SQLite" as SQLite
Visitor --> Routes : HTTP GET / POST
Routes --> Templates : render pages
Routes --> Forms : validate demo inputs
Routes --> Models : query events
Models --> SQLite : SQL
@enduml
```

## 4. Sequence diagram — browse event details

```plantuml
@startuml
actor Visitor
participant "Browser" as Browser
participant "Flask Routes" as Routes
participant "SQLAlchemy" as ORM
database "SQLite" as DB
Visitor -> Browser : Select event card
Browser -> Routes : GET /events/{id}
Routes -> ORM : Fetch event by ID
ORM -> DB : SELECT event
DB --> ORM : Row or no result
ORM --> Routes : Event or 404
alt Event exists
  Routes --> Browser : Render event_detail.html
  Browser --> Visitor : Event information
else Event missing
  Routes --> Browser : 404 Not Found
end
@enduml
```

## 5. Future-facing boundary

The database includes `User`, `Seat`, and `Booking` to document the planned domain. The V1 HTTP interface intentionally **does not expose** registration persistence, authentication, seat reservation, cancellation, or checkout endpoints.
