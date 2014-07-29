execfile('test_api.py')

c = Connection()
e = c.get_event('a')
u1 = e.create_user('a','a','','','')
u2 = e.create_user('b','b','','','')

print "User 1: %s"%u1.id
print "User 2: %s"%u2.id

print "Connecting first user"
u1.connect()
print "Connecting second user"
u2.connect()

print "Waiting..."
time.sleep(5)

print "Disconneting one user"
u1.disconnect()

print "Waiting.."
time.sleep(3)
print "Disconnecting second user"
u2.disconnect()
print "Done."