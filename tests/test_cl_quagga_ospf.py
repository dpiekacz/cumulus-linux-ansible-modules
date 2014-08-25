import mock
from mock import MagicMock
from nose.tools import set_trace
from dev_modules.cl_quagga_ospf import check_dsl_dependencies, main, \
    has_interface_config, get_running_config, update_router_id, \
    add_global_ospf_config, update_reference_bandwidth, \
    get_interface_addr_config, check_ip_addr_show, \
    config_ospf_interface_config
from asserts import assert_equals


@mock.patch('dev_modules.cl_quagga_ospf.run_cl_cmd')
@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_check_ip_addr_show(mock_module,
                            mock_run_cl_cmd):
    instance = mock_module.return_value
    mock_run_cl_cmd.return_value = \
        ['55: swp52s0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 9000 qdisc ',
         '    link/ether 44:38:39:00:26:14 brd ff:ff:ff:ff:ff:ff',
         '    inet 10.1.1.1/24 scope global swp52s0']
    assert_equals(check_ip_addr_show(instance), True)
    # no ip address found in ip addr show
    mock_run_cl_cmd.return_value = \
        ['55: swp52s0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 9000 qdisc ',
         '    link/ether 44:38:39:00:26:14 brd ff:ff:ff:ff:ff:ff']
    assert_equals(check_ip_addr_show(instance), False)


@mock.patch('dev_modules.cl_quagga_ospf.run_cl_cmd')
@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_get_interface_address_config(mock_module,
                                      mock_run_cl_cmd):
    """
    cl_quagga_ospf - test if interface addr is present
    """
    instance = mock_module.return_value
    mock_run_cl_cmd.return_value = ''.join(
        ['[', '    {', '        "auto": true,',
         '        "config": {', '            "address": "10.1.1.1/24",',
         '            "mtu": "9000"', '        },',
         '        "addr_method": null,', '        "name": "swp52s0",',
         '        "addr_family": null', '    }', ']'])
    assert_equals(get_interface_addr_config(instance), True)


@mock.patch('dev_modules.cl_quagga_ospf.config_ospf_interface_config')
@mock.patch('dev_modules.cl_quagga_ospf.add_global_ospf_config')
@mock.patch('dev_modules.cl_quagga_ospf.has_interface_config')
@mock.patch('dev_modules.cl_quagga_ospf.check_dsl_dependencies')
@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_check_mod_args(mock_module,
                        mock_check_dsl_dependencies,
                        mock_has_interface_config,
                        mock_add_global_ospf,
                        mock_config_ospf_int):
    """
    cl_quagga_ospf - check mod args
    """
    instance = mock_module.return_value
    instance.params.get.return_value = MagicMock()
    main()
    mock_module.assert_called_with(argument_spec={
        'router_id': {'type': 'str'},
        'area': {'default': '0.0.0.0', 'type': 'str'},
        'reference_bandwidth': {
            'default': '40000',
            'type': 'str'
        },
        'saveconfig': {
            'default': False,
            'choices': ['yes', 'on', '1', 'true',
                        1, 'no', 'off', '0',
                        'false', 0]},
        'state': {'type': 'str', 'choices': ['present', 'absent']},
        'cost': {'type': 'str'}, 'interface': {'type': 'str'},
        'point2point': {'default': False,
                        'choices': ['yes', 'on', '1',
                                    'true', 1, 'no',
                                    'off', '0', 'false', 0]}},
        mutually_exclusive=[
            ['reference_bandwidth', 'interface'],
            ['router_id', 'interface']]
    )
    assert_equals(mock_check_dsl_dependencies.call_args_list[0],
                  mock.call(instance, ['cost', 'state', 'area',
                                       'point2point', 'passive'],
                            'interface', 'swp1'))
    assert_equals(mock_check_dsl_dependencies.call_args_list[1],
                  mock.call(instance, ['interface'], 'area', '0.0.0.0'))


@mock.patch('dev_modules.cl_quagga_ospf.run_cl_cmd')
@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_get_running_config(mock_module,
                            mock_run_cl_cmd):
    """
    cl_quagga_ospf - test getting vtysh running config
    """
    output = open('tests/vtysh.txt').read()
    mock_run_cl_cmd.return_value = output.split('\n')
    instance = mock_module.return_value
    get_running_config(instance)
    assert_equals(instance.global_config,
                  ['ospf router-id 10.100.1.1',
                   'auto-cost reference-bandwidth 40000'])
    # check that interface config is done right
    assert_equals(len(instance.interface_config.keys()), 57)
    assert_equals(instance.interface_config.get('swp52s0'),
                  ['ip ospf area 0.0.0.0',
                   'ip ospf network point-to-point',
                   'ipv6 nd suppress-ra', 'link-detect'])
    mock_run_cl_cmd.assert_called_with(instance,
                                       '/usr/bin/vtysh -c "show run"')


def mod_args_global_ospf_config(arg):
    values = {
        'router_id': '10.1.1.1',
        'reference_bandwidth': '40000'
    }
    return values[arg]


@mock.patch('dev_modules.cl_quagga_ospf.run_cl_cmd')
@mock.patch('dev_modules.cl_quagga_ospf.get_config_line')
@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_update_router_id(mock_module,
                          mock_get_config_line,
                          mock_run_cl_cmd):
    """
    cl_quagga_ospf - updating router_id
    """
    instance = mock_module.return_value
    instance.exit_msg = ''
    instance.params.get.return_value = '10.1.1.1'
    # no router id defined
    mock_get_config_line.return_value = None
    update_router_id(instance)
    assert_equals(instance.exit_msg, 'router-id updated ')
    assert_equals(instance.has_changed, True)
    cmd_line = '/usr/bin/cl-ospf router-id set 10.1.1.1'
    mock_run_cl_cmd.assert_called_with(instance, cmd_line)
    # router id is different
    instance.exit_msg = ''
    instance.has_changed = False
    mock_get_config_line.return_value = 'ospf router-id 10.2.2.2'
    update_router_id(instance)
    assert_equals(instance.exit_msg, 'router-id updated ')
    assert_equals(instance.has_changed, True)
    cmd_line = '/usr/bin/cl-ospf router-id set 10.1.1.1'
    mock_run_cl_cmd.assert_called_with(instance, cmd_line)
    # router id is the same
    instance.exit_msg = ''
    instance.has_changed = False
    mock_get_config_line.return_value = 'ospf router-id 10.1.1.1'
    update_router_id(instance)
    assert_equals(instance.exit_msg, '')
    assert_equals(instance.has_changed, False)


@mock.patch('dev_modules.cl_quagga_ospf.run_cl_cmd')
@mock.patch('dev_modules.cl_quagga_ospf.get_config_line')
@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_update_reference_bandwidth(mock_module,
                                    mock_get_config_line,
                                    mock_run_cl_cmd):
    """
    cl_quagga_ospf - test updating reference bandwidth
    """
    instance = mock_module.return_value
    instance.exit_msg = ''
    instance.params.get.return_value = '40000'
    # no reference bandwidth defined - highly unlikely since default is set
    mock_get_config_line.return_value = None
    change_msg = 'reference bandwidth updated '
    update_reference_bandwidth(instance)
    assert_equals(instance.exit_msg, change_msg)
    assert_equals(instance.has_changed, True)
    cmd_line = '/usr/bin/cl-ospf auto-cost set reference-bandwidth 40000'
    mock_run_cl_cmd.assert_called_with(instance, cmd_line)
    # reference bandwidth is different
    instance.exit_msg = ''
    instance.has_changed = False
    mock_get_config_line.return_value = 'auto-cost reference-bandwidth 45000'
    update_reference_bandwidth(instance)
    assert_equals(instance.exit_msg, change_msg)
    assert_equals(instance.has_changed, True)
    mock_run_cl_cmd.assert_called_with(instance, cmd_line)
    # router id is the same
    instance.exit_msg = ''
    instance.has_changed = False
    mock_get_config_line.return_value = 'auto-cost reference-bandwidth 40000'
    update_reference_bandwidth(instance)
    assert_equals(instance.exit_msg, '')
    assert_equals(instance.has_changed, False)


@mock.patch('dev_modules.cl_quagga_ospf.get_running_config')
@mock.patch('dev_modules.cl_quagga_ospf.get_interface_addr_config')
@mock.patch('dev_modules.cl_quagga_ospf.enable_or_disable_ospf_on_int')
@mock.patch('dev_modules.cl_quagga_ospf.update_point2point')
@mock.patch('dev_modules.cl_quagga_ospf.update_cost')
@mock.patch('dev_modules.cl_quagga_ospf.update_passive')
@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_config_ospf_interface_config(mock_module,
                                      mock_update_passive,
                                      mock_update_cost,
                                      mock_update_point2point,
                                      mock_ospf_on_int,
                                      mock_get_interface_addr,
                                      mock_get_running_config):
    instance = mock_module.return_value
    manager = mock.Mock()
    manager.attach_mock(mock_get_running_config, 'get_running_config')
    manager.attach_mock(mock_get_interface_addr, 'get_interface_addr_config')
    manager.attach_mock(mock_ospf_on_int, 'enable_or_disable_ospf_on_int')
    manager.attach_mock(mock_update_point2point, 'update_point2point')
    manager.attach_mock(mock_update_cost, 'update_cost')
    manager.attach_mock(mock_update_passive, 'update_passive')
    # enable the ospf interface
    expected_calls = [mock.call.get_running_config(instance),
                      mock.call.get_interface_addr_config(instance),
                      mock.call.enable_or_disable_ospf_on_int(instance),
                      mock.call.update_point2point(instance),
                      mock.call.update_cost(instance),
                      mock.call.update_passive(instance)]
    config_ospf_interface_config(instance)
    assert_equals(manager.method_calls, expected_calls)
    # disable ospf on the interface
    mock_ospf_on_int.return_value = False
    manager = mock.Mock()
    manager.attach_mock(mock_get_running_config, 'get_running_config')
    manager.attach_mock(mock_get_interface_addr, 'get_interface_addr_config')
    manager.attach_mock(mock_ospf_on_int, 'enable_or_disable_ospf_on_int')
    manager.attach_mock(mock_update_point2point, 'update_point2point')
    manager.attach_mock(mock_update_cost, 'update_cost')
    manager.attach_mock(mock_update_passive, 'update_passive')
    expected_calls = [mock.call.get_running_config(instance),
                      mock.call.get_interface_addr_config(instance),
                      mock.call.enable_or_disable_ospf_on_int(instance)]
    config_ospf_interface_config(instance)
    assert_equals(manager.method_calls, expected_calls)



@mock.patch('dev_modules.cl_quagga_ospf.update_reference_bandwidth')
@mock.patch('dev_modules.cl_quagga_ospf.get_running_config')
@mock.patch('dev_modules.cl_quagga_ospf.update_router_id')
@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_add_global_ospf_config(mock_module,
                                mock_update_router_id,
                                mock_get_running_config,
                                mock_reference_bandwidth):
    """
    cl_quagga_ospf - test setting global ospfv2 config
    """
    instance = mock_module.return_value
    instance.params.get.side_effect = mod_args_global_ospf_config
    manager = mock.Mock()
    manager.attach_mock(mock_get_running_config, 'get_running_config')
    manager.attach_mock(mock_update_router_id, 'update_router_id')
    manager.attach_mock(mock_reference_bandwidth, 'update_reference_bandwidth')
    add_global_ospf_config(instance)
    expected_calls = [mock.call.get_running_config(instance),
                      mock.call.update_router_id(instance),
                      mock.call.update_reference_bandwidth(instance)]
    # check order of functions called
    assert_equals(manager.method_calls, expected_calls)
    # ensure exit_json is called at the end of the function with a change or no
    # change
    assert_equals(instance.exit_json.call_count, 1)


@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_has_int_config(mock_module):
    """
    cl_quagga_ospf - get interface config from quagga. TODO get from ifquery
    """
    instance = mock_module.return_value
    instance.params = {'interface': '', 'state': ''}
    assert_equals(has_interface_config(instance), True)
    instance.params = {'state': ''}
    assert_equals(has_interface_config(instance), False)


def check_dsl_args(arg):
    values = {
        'cost': None,
        'state':  None,
        'point2point': 'yes',
        'interface': None,
    }
    return values[arg]


@mock.patch('dev_modules.cl_quagga_ospf.AnsibleModule')
def test_check_dsl_dependencies(mock_module):
    """
    cl_quagga_ospf - check dsl dependencies
    """
    instance = mock_module.return_value
    instance.params.get.side_effect = check_dsl_args
    _input_options = ['point2point', 'cost']
    _depends = 'interface'
    check_dsl_dependencies(instance, _input_options, _depends, 'swp1')
    instance.fail_json.assert_called_with(
        msg="incorrect syntax. point2point must have an " +
        "interface option. Example 'cl_quagga_ospf: interface=swp1 " +
        "point2point=yes'"
    )
