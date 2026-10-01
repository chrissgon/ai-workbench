# Brief: Cragline booking

- Status: approved by the user on 2026-09-18
- Topic: cragline-booking
- Raised by: core-clarify

## Request, in the user's words

"Our climbing gym takes class bookings on a paper sheet at the front desk and by phone. People book and do not show up, and the desk spends the evening on the phone. I want members to book and cancel classes themselves, and the desk to see who is coming."

## What exists today

- A paper sheet per class at the front desk; bookings by phone or in person.
- No website feature for booking; the gym's website is a static page with the timetable.
- The front desk counted no-shows on the paper sheets for August 2026: 22% of booked places were no-shows.

## Decisions

1. The product is a web application for booking the gym's classes. It replaces the paper sheet. (user, 2026-09-18)
2. Two audiences and no others: gym members who book classes, and front-desk staff who run the classes' attendance. (user, 2026-09-18)
3. In scope for launch: members see the timetable with free places, book a place, cancel a booking; staff see the attendee list of each class and mark who attended. (user, 2026-09-18)
4. A waiting list for full classes and reminder messages before a class come after launch, as a second phase. (user, 2026-09-18)
5. Out of scope: payments and memberships (they stay in the existing till system), and a native mobile application. (user, 2026-09-18)
6. Goal: fewer booked places left empty. Target: no-show rate below 10% of booked places, measured on the attendance marks, against the 22% counted in August 2026. (user, 2026-09-18)
7. Second goal: the front desk stops taking bookings by phone. No target was set. (user, 2026-09-18)
8. Constraint: it must work in a phone browser, because members book from their phones. Constraint: hosted on the gym's existing shared web hosting, which runs PHP and MySQL only. (user, 2026-09-18)

## Not decided

- When the product launches.
- How a member proves who they are (member number, email link or something else).
