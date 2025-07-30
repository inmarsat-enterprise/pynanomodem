# pynanomodem

## Legacy IDP Modem

### Concept of Operation

* Power on
* Await GNSS
* Await registration
* Optional configure wakeup period and power mode
* Periodically check for new MT message, polling or triggered by event line
or URC
    * Retrieve the message using its ID
    * Ensure Rx dequeued
* When sending:
    * Submit message and get ID
    * Periodically check for completion state, polling or triggered by event
    line or URC
    * Ensure Tx dequeued
* Periodically check network state for change
* Optional query location

## OGx Modem

### Concept of Operation

* Power on
* ...
