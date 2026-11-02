# CSTBS Version 2 — UML Diagrams (PlantUML)

Diagrams below document implemented **Accounts and Events** behavior. Seat and Booking remain schema-only until a later version.

## 1. Use cases

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
rectangle "CSTBS V2" {
  usecase "Browse events" as Browse
  usecase "View event detail" as Detail
  usecase "Register student account" as Register
  usecase "Log in / out" as Auth
  usecase "View own account" as Account
  usecase "Create event" as Create
  usecase "Edit event" as Edit
  usecase "Delete event" as Delete
}
Visitor --> Browse
Visitor --> Detail
Visitor --> Register
Visitor --> Auth
Student --> Account
Staff --> Account
Admin --> Account
Admin --> Create
Admin --> Edit
Admin --> Delete
@enduml
```

## 2. Class diagram

```plantuml
@startuml
skinparam classAttributeIconSize 0
class User {
  +id: Integer
  +full_name: String
  +email: String [unique]
  +password_hash: String
  +role: student|staff|admin
  +created_at: DateTime
  +set_password(password)
  +check_password(password): bool
  +is_admin: bool
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
User "1" -- "0..*" Booking
Event "1" -- "0..*" Seat
Seat "1" -- "0..*" Booking
@enduml
```

## 3. Component diagram

```plantuml
@startuml
skinparam componentStyle rectangle
actor Visitor
actor Admin
component "Flask Routes" as Routes
component "Flask-Login / Auth" as Auth
component "Flask-WTF / CSRF" as Forms
component "Jinja2 Templates" as View
component "SQLAlchemy Models" as ORM
database "SQLite" as DB
Visitor --> Routes : browse / account HTTP
Admin --> Routes : admin event HTTP
Routes --> Auth : sessions & role checks
Routes --> Forms : validate inputs
Routes --> ORM : CRUD
Routes --> View : render pages
ORM --> DB : SQL
@enduml
```

## 4. Sequence: user login

```plantuml
@startuml
actor User
participant Browser
participant "Flask route" as Route
participant "Flask-WTF" as Form
participant "User model / Werkzeug" as Model
participant "Flask-Login" as Login
User -> Browser : Enter email and password
Browser -> Route : POST /login + CSRF
Route -> Form : validate_on_submit()
alt invalid input / CSRF
  Route --> Browser : Form errors / HTTP 400
else valid input
  Route -> Model : Find user by email, check_password()
  alt Password valid
    Route -> Login : login_user(user)
    Route --> Browser : Redirect to account / safe next
  else Invalid credentials
    Route --> Browser : Generic login failure message
  end
end
@enduml
```

## 5. Sequence: administrator creates event

```plantuml
@startuml
actor Admin
participant Browser
participant "Flask endpoint" as Route
participant "Flask-Login" as Auth
participant "EventForm" as Form
participant "SQLAlchemy" as ORM
Admin -> Browser : Open create event screen
Browser -> Route : GET /admin/events/new
Route -> Auth : @login_required + admin_required
alt Not authenticated
  Route --> Browser : Redirect to /login
else Signed in, non-admin
  Route --> Browser : 403 Forbidden
else Admin
  Route --> Browser : Render form
  Browser -> Route : POST event data + CSRF
  Route -> Form : Validate fields and CSRF
  alt Valid
    Route -> ORM : INSERT Event
    Route --> Browser : Redirect to public details
  else Invalid
    Route --> Browser : Render field errors
  end
end
@enduml
```
