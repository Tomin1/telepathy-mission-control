"""Regression test for dispatching an incoming Text channel.
"""

import dbus
import dbus.bus
import dbus.service

from servicetest import EventPattern, tp_name_prefix, tp_path_prefix, \
        call_async, sync_dbus
from mctest import exec_test, SimulatedConnection, SimulatedClient, \
        create_fakecm_account, enable_fakecm_account, SimulatedChannel, \
        expect_client_setup
import constants as cs

def test(q, bus, mc):
    params = dbus.Dictionary({"account": "someguy@example.com",
        "password": "secrecy"}, signature='sv')
    cm_name_ref, account = create_fakecm_account(q, bus, mc, params)
    conn = enable_fakecm_account(q, bus, mc, account, params)

    text_fixed_properties = dbus.Dictionary({
        cs.CHANNEL + '.TargetHandleType': cs.HT_CONTACT,
        cs.CHANNEL + '.ChannelType': cs.CHANNEL_TYPE_TEXT,
        }, signature='sv')

    empathy_bus = dbus.bus.BusConnection()
    q.attach_to_bus(empathy_bus)
    empathy = SimulatedClient(q, empathy_bus, 'Empathy',
            observe=[text_fixed_properties], approve=[text_fixed_properties],
            handle=[text_fixed_properties], bypass_approval=False)

    # wait for MC to download the properties
    expect_client_setup(q, [empathy])

    # subscribe to the OperationList interface (MC assumes that until this
    # property has been retrieved once, nobody cares)

    cd = bus.get_object(cs.CD, cs.CD_PATH)
    cd_props = dbus.Interface(cd, cs.PROPERTIES_IFACE)
    assert cd_props.Get(cs.CD_IFACE_OP_LIST, 'DispatchOperations') == []

    channel_properties = dbus.Dictionary(text_fixed_properties,
            signature='sv')
    channel_properties[cs.CHANNEL + '.TargetID'] = 'juliet'
    channel_properties[cs.CHANNEL + '.TargetHandle'] = \
            conn.ensure_handle(cs.HT_CONTACT, 'juliet')
    channel_properties[cs.CHANNEL + '.InitiatorID'] = 'juliet'
    channel_properties[cs.CHANNEL + '.InitiatorHandle'] = \
            conn.ensure_handle(cs.HT_CONTACT, 'juliet')
    channel_properties[cs.CHANNEL + '.Requested'] = False
    channel_properties[cs.CHANNEL + '.Interfaces'] = dbus.Array(signature='s')

    chan = SimulatedChannel(conn, channel_properties)
    chan.announce()

    # A channel dispatch operation is created

    e = q.expect('dbus-signal',
            path=cs.CD_PATH,
            interface=cs.CD_IFACE_OP_LIST,
            signal='NewDispatchOperation')

    cdo_path = e.args[0]
    cdo_properties = e.args[1]

    assert cdo_properties[cs.CDO + '.Account'] == account.object_path
    assert cdo_properties[cs.CDO + '.Connection'] == conn.object_path
    assert cs.CDO + '.Interfaces' in cdo_properties

    handlers = cdo_properties[cs.CDO + '.PossibleHandlers'][:]
    assert handlers == [cs.tp_name_prefix + '.Client.Empathy'], handlers

    assert cs.CD_IFACE_OP_LIST in cd_props.Get(cs.CD, 'Interfaces')
    assert cd_props.Get(cs.CD_IFACE_OP_LIST, 'DispatchOperations') ==\
            [(cdo_path, cdo_properties)]

    cdo = bus.get_object(cs.CD, cdo_path)
    cdo_iface = dbus.Interface(cdo, cs.CDO)
    cdo_props_iface = dbus.Interface(cdo, cs.PROPERTIES_IFACE)

    assert cdo_props_iface.Get(cs.CDO, 'Interfaces') == \
            cdo_properties[cs.CDO + '.Interfaces']
    assert cdo_props_iface.Get(cs.CDO, 'Connection') == conn.object_path
    assert cdo_props_iface.Get(cs.CDO, 'Account') == account.object_path
    assert cdo_props_iface.Get(cs.CDO, 'Channels') == [(chan.object_path,
        channel_properties)]
    assert cdo_props_iface.Get(cs.CDO, 'PossibleHandlers') == \
            cdo_properties[cs.CDO + '.PossibleHandlers']

    e = q.expect('dbus-method-call',
            path=empathy.object_path,
            interface=cs.OBSERVER, method='ObserveChannels',
            handled=False)
    assert e.args[0] == account.object_path, e.args
    assert e.args[1] == conn.object_path, e.args
    assert e.args[3] == cdo_path, e.args
    assert e.args[4] == [], e.args      # no requests satisfied
    channels = e.args[2]
    assert len(channels) == 1, channels
    assert channels[0][0] == chan.object_path, channels
    assert channels[0][1] == channel_properties, channels

    q.dbus_return(e.message, bus=empathy_bus, signature='')

    e = q.expect('dbus-method-call',
            path=empathy.object_path,
            interface=cs.APPROVER, method='AddDispatchOperation',
            handled=False)

    assert e.args == [[(chan.object_path, channel_properties)],
            cdo_path, cdo_properties]

    q.dbus_return(e.message, bus=empathy_bus, signature='')

    call_async(q, cdo_iface, 'HandleWith',
            cs.tp_name_prefix + '.Client.Empathy')

    # Empathy is asked to handle the channels
    e, _, _, _ = q.expect_many(
            EventPattern('dbus-method-call',
                path=empathy.object_path,
                interface=cs.HANDLER, method='HandleChannels',
                handled=False),
            # FIXME: currently HandleWith succeeds immediately, rather than
            # failing when HandleChannels fails (fd.o #21003)
            EventPattern('dbus-return', method='HandleWith'),
            EventPattern('dbus-signal', interface=cs.CDO, signal='Finished'),
            EventPattern('dbus-signal', interface=cs.CD_IFACE_OP_LIST,
                signal='DispatchOperationFinished'),
            )

    # Empathy rejects the channels
    q.dbus_raise(e.message, cs.NOT_AVAILABLE, 'Blind drunk', bus=empathy_bus)

    # Now there are no more active channel dispatch operations
    assert cd_props.Get(cs.CD_IFACE_OP_LIST, 'DispatchOperations') == []

if __name__ == '__main__':
    exec_test(test, {})
