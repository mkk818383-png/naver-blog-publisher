# V2 content-type templates

This contract selects modules by `content_type`. Unknown and missing types fail
closed; restaurant language is never a default for another type.

## Common flow

Every published narrative follows this order, with the type-specific modules
placed at the matching step: visit motive → place information → access or use
information → offering exploration → chosen item or service → use process →
space or setting → tips and limitations → overall review.

## `restaurant`

### Required modules

- visit motive
- place information
- access or parking
- menu exploration
- chosen dishes
- dining process
- overall review

### Optional modules

- side dishes
- serving order
- additional order
- seating

### Forbidden modules

- check-in
- treatment aftercare
- product fitting

### Ordered flow

visit motive → place information → access or parking → menu exploration → chosen dishes → side dishes → dining process → serving order → overall review

## `cafe`

### Required modules

- visit motive
- place information
- access or parking
- drink or dessert exploration
- chosen drinks or desserts
- stay flow
- overall review

### Optional modules

- showcase
- seating
- window view
- takeout

### Forbidden modules

- side dishes
- serving order
- eating method

### Ordered flow

visit motive → place information → access or parking → drink or dessert exploration → chosen drinks or desserts → showcase → seating → stay flow → overall review

## `accommodation`

### Required modules

- stay motive
- property information
- reservation or arrival information
- check-in
- room
- facilities
- overall review

### Optional modules

- nearby route
- checkout
- amenity notes
- accessibility

### Forbidden modules

- side dishes
- menu exploration
- treatment process

### Ordered flow

stay motive → property information → reservation or arrival information → check-in → room → facilities → nearby route → overall review

## `experience`

### Required modules

- participation motive
- venue information
- reservation information
- preparation
- progress steps
- result
- overall review

### Optional modules

- difficulty
- instructor guidance
- safety notes
- take-home care

### Forbidden modules

- side dishes
- dining process
- room tour

### Ordered flow

participation motive → venue information → reservation information → preparation → progress steps → result → difficulty → overall review

## `beauty`

### Required modules

- visit motive
- salon information
- reservation information
- consultation
- treatment process
- aftercare
- overall review

### Optional modules

- before and after record
- stylist guidance
- maintenance timing
- seating comfort

### Forbidden modules

- side dishes
- menu exploration
- product fitting

### Ordered flow

visit motive → salon information → reservation information → consultation → treatment process → before and after record → aftercare → overall review

## `retail`

### Required modules

- shopping motive
- store information
- access information
- product exploration
- selected products
- fitting or purchase process
- overall review

### Optional modules

- stock check
- gift wrapping
- exchange policy
- display layout

### Forbidden modules

- side dishes
- treatment process
- check-in

### Ordered flow

shopping motive → store information → access information → product exploration → selected products → fitting or purchase process → exchange policy → overall review
