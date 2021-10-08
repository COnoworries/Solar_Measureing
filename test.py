import pyudev

context = pyudev.Context()
device_list = (device.device_node for device in context.list_devices(subsystem='block', DEVTYPE='partition'))
print(device_list)