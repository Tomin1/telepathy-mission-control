"""Regression test for recovering from an MC crash.
"""

import os

import dbus
import dbus.service

from servicetest import EventPattern, call_async
from mctest import exec_test, SimulatedConnection, SimulatedClient, \
        create_fakecm_account, enable_fakecm_account, SimulatedChannel, \
        expect_client_setup, make_mc
import constants as cs

def preseed():
    accounts_dir = os.environ['MC_ACCOUNT_DIR']

    accounts_cfg = open(accounts_dir + '/accounts.cfg', 'w')

    accounts_cfg.write("""# Telepathy accounts
[fakecm/fakeprotocol/jc_2edenton_40unatco_2eint]
manager=fakecm
protocol=fakeprotocol
DisplayName=Work account
NormalizedName=jc.denton@unatco.int
param-account=jc.denton@unatco.int
param-password=ionstorm
Enabled=1
""")

    accounts_cfg.close()

    account_connections_file = open(accounts_dir + '/.mc_connections', 'w')

    account_connections_file.write("%s\t%s\t%s\n" %
            (cs.tp_path_prefix + '/Connection/fakecm/fakeprotocol/jc',
                cs.tp_name_prefix + '.Connection.fakecm.fakeprotocol.jc',
                'fakecm/fakeprotocol/jc_2edenton_40unatco_2eint'))

def test(q, bus, unused):
    text_fixed_properties = dbus.Dictionary({
        cs.CHANNEL + '.TargetHandleType': cs.HT_CONTACT,
        cs.CHANNEL + '.ChannelType': cs.CHANNEL_TYPE_TEXT,
        }, signature='sv')

    conn = SimulatedConnection(q, bus, 'fakecm', 'fakeprotocol',
            'jc', 'jc.denton@unatco.int')
    conn.StatusChanged(cs.CONN_STATUS_CONNECTED, 0)

    unhandled_properties = dbus.Dictionary(text_fixed_properties, signature='sv')
    unhandled_properties[cs.CHANNEL + '.Interfaces'] = dbus.Array(signature='s')
    unhandled_properties[cs.CHANNEL + '.TargetID'] = 'anna.navarre@unatco.int'
    unhandled_properties[cs.CHANNEL + '.TargetHandle'] = \
            dbus.UInt32(conn.ensure_handle(cs.HT_CONTACT, 'anna.navarre@unatco.int'))
    unhandled_properties[cs.CHANNEL + '.InitiatorHandle'] = dbus.UInt32(conn.self_handle)
    unhandled_properties[cs.CHANNEL + '.InitiatorID'] = conn.self_ident
    unhandled_properties[cs.CHANNEL + '.Requested'] = True
    unhandled_chan = SimulatedChannel(conn, unhandled_properties)
    unhandled_chan.announce()

    handled_properties = dbus.Dictionary(text_fixed_properties, signature='sv')
    handled_properties[cs.CHANNEL + '.Interfaces'] = dbus.Array(signature='s')
    handled_properties[cs.CHANNEL + '.TargetID'] = 'gunther.hermann@unatco.int'
    handled_properties[cs.CHANNEL + '.TargetHandle'] = \
            dbus.UInt32(conn.ensure_handle(cs.HT_CONTACT, 'gunther.hermann@unatco.int'))
    handled_properties[cs.CHANNEL + '.InitiatorHandle'] = dbus.UInt32(conn.self_handle)
    handled_properties[cs.CHANNEL + '.InitiatorID'] = conn.self_ident
    handled_properties[cs.CHANNEL + '.Requested'] = True
    handled_chan = SimulatedChannel(conn, handled_properties)
    handled_chan.announce()

    client = SimulatedClient(q, bus, 'Empathy',
            observe=[text_fixed_properties], approve=[text_fixed_properties],
            handle=[text_fixed_properties], bypass_approval=False)

    # service-activate MC
    mc = make_mc(bus, q.append)

    e = q.expect('dbus-method-call',
            args=[cs.HANDLER, 'HandledChannels'],
            path=client.object_path,
            handled=False,
            interface=cs.PROPERTIES_IFACE,
            method='Get')
    # Empathy is handling one of the channels
    q.dbus_return(e.message, dbus.Array([handled_chan.object_path],
        signature='o'), signature='v')

    # we're told about the other channel as an observer...
    e = q.expect('dbus-method-call',
            path=client.object_path,
            interface=cs.OBSERVER, method='ObserveChannels',
            handled=False)
    assert e.args[1] == conn.object_path, e.args
    channels = e.args[2]
    assert channels[0][0] == unhandled_chan.object_path, channels
    q.dbus_return(e.message, signature='')

    # ... and as a handler
    e = q.expect('dbus-method-call',
            path=client.object_path,
            interface=cs.HANDLER, method='HandleChannels',
            handled=False)
    assert e.args[1] == conn.object_path, e.args
    channels = e.args[2]
    assert channels[0][0] == unhandled_chan.object_path, channels
    q.dbus_return(e.message, signature='')

if __name__ == '__main__':
    preseed()
    exec_test(test, {}, preload_mc=False)