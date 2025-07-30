# pynanomodem

A Python library/package for interfacing to modems using Viasat's
[**IoT Nano**](https://www.viasat.com/enterprise/services/iot-nano)
satellite IoT service.

IoT Nano is a **Non-IP** messaging service offering very low power consumption,
low cost modules and devices for small amounts of data.
IoT Nano is intended for event-based remote data collection and device remote
control, combining two network protocols sharing the same global coverage:

* IDP (aka IsatData Pro) is a mature global service offering message size up
to about 5 kilobytes, relatively low latency of less than 20 seconds for small
messages and low throughput about 0.1 kbps.
* OGx offers various improvements to IDP such as lower power consuming
configurations, larger messages and faster throughput for larger messages.

These network protocols are optimized for geostationary satellite use, developed
by ORBCOMM in partnership with Viasat. The service(s) operate over the Viasat
global L-band global network and can be procured through a varietry of
authorized Viasat IoT service partners.

Example modems available:
* [Quectel CC200A-LB](https://www.quectel.com/product/cc200a-lb-satellite-communication-module)
* [ORBCOMM ST2100](https://www.orbcomm.com/en/partners/iot-hardware/st-2100)
* [ORBCOMM ST4000 / uBlox UBX-S52](https://content.u-blox.com/sites/default/files/documents/UBX-R52-S52_ProductSummary_UBX-19026227.pdf)

> [!NOTE]
> Obsoletes/replaces the Inmarsat `idpmodem` and `pynimomodem` projects.

## Installation and Use

Installing using pip:
```
pip install 'pynanomodem'
```

The library provides an abstract base class to encapsulate manufacturer-specific
AT commands as a common set of methods such as:

* `mo_message_send`
* `mt_message_recv`
* `get_location`
* `set_wakeup_interval`
* `get_network_state`

Viasat and/or manufacturers provide model-specific subclasses through
access to GitHub repositories based on mutual non-disclosure agreement.

## Background

### System Overview

*IoT Nano* is a store-and-forward satellite messaging technology
with flexible message sizes offering 2-way remote communications.

***Message***s are sent to or collected from a ***Device*** using its globally
unique *Device ID* (aka Mobile ID),
transacted through a ***Mailbox*** that provides authentication, encryption and
data segregation for cloud-based or enterprise client applications via a
REST **Messaging API**.

Messages can be *Mobile-Originated* (**MO**) sent by the remote device, or
*Mobile-Terminated* (**MT**) sent to the device.

Sensors and controls in the field are typically interfaced to a microcontroller
unit (MCU) connected to a satellite modem using a serial
interface with *AT commands* to send and receive messages, check network status,
and optionally use the built-in *Global Navigation Satellite System* (GNSS)
receiver to determine location-based information.

The first byte of the message is referred to as the
*Service Identification Number* (**SIN**) where values below 16 are reserved
for system use.  SIN is intended to capture the concept of embedded
microservices used by an application.

The second byte of the message can optionally be defined as the
*Message Identifier Number* (**MIN**) intended to support remote operations 
within each *SIN* embedded microservice with predefined binary formatting.
The *MIN* concept also supports an optional *codec* feature
allowing an XML file to be applied to a Mailbox to decode binary data into
a JSON-tagged message structure for easier integration to cloud applications.

### Modem Concept of Operation

1. Upon power-up or reset, the modem first acquires its location using 
Global Navigation Satellite Systems (GNSS).
1. After getting its location, the modem tunes to the correct frequency, then
registers on the network.  Once registered it can communicate on the
network.
1. MO messages are submitted by a microcontroller or IoT Edge device, which
then must monitor progress until the message is complete (either delivered or
timed out/failed due to blockage). Completed messages must then be cleared from
the modem transmit queue.
1. MT messages that arrive are stored in the modem's receive queue and the MCU
queries for *new* MT messages periodically or when prompted by the modem's
event notification mechanisms, if configured.
1. Network acquisition status and signal strength can also be queried using AT
commands.
1. Power saving features can be configured locally using AT commands or remotely
using the Messaging API. The primary mechanism for power savings is a
configurable *wakeup interval* that gets negotiated with the network so that
the network can store MT messages until the next modem wakeup.
1. If the modem cannot find the target frequency it begins to search for other
frequencies from a configuration map in its non-volatile memory. It will cycle
through beam acquisition attempts for a period of time before falling back to
a globally-accessible frequency where it may need to download
a new network configuration before re-attempting.
1. Prolonged obstruction of satellite signal will put the modem into *blockage*
state from which it will automatically try to recover based on an algorithm
influenced by its *power mode* setting.

## More Information

To find out more details about system integration and the detailed operation
of the IoT Nano service, please contact your local Viasat representative or
authorized distributor to sign a mutual non-disclosure agreement and
request access to the
[IoT Nano Developer Kit](https://github.com/inmarsat-enterprise/idp-developer-kit-nda)
repository.