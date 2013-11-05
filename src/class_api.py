import os
import sys
import time


#A hack to let pybitmessage source directory exist as Subdir for testing
if os.path.exists(os.path.abspath('PyBitmessage')):
    sys.path.append(os.path.abspath('PyBitmessage/src'))


class APIError(Exception):
    def __init__(self, error_message):
        self.error_message = error_message
    def __str__(self):
        return "API Error: %s" % self.error_message

def getAPI(workingdir=None,silent=False):
    
    if workingdir:
        os.environ["BITMESSAGE_HOME"] = workingdir
    
    #Workaround while logging is not completed 
    if silent:
        import StringIO
        fobj = StringIO.StringIO()
        sys.stdout = fobj    
        
    import bitmessagemain
    class MainAPI(bitmessagemain.Main):

        def addToAddressBook(self, label, address):

            '''Add a Conact to the Addressbook
            Usage: api.addContact(label,bmaddress)'''

            unicode(label, 'utf-8')
            queryreturn = bitmessagemain.shared.sqlQuery('''select * from addressbook where address=?''',address)
            if queryreturn != []:
                raise APIError('Given Address is already inside: %s'%address)
            queryreturn = bitmessagemain.shared.sqlExecute('''INSERT INTO addressbook VALUES (?,?)''',label, address)

        def addSubscription(self, label, address):
            
            '''Add a Subscription
            Usage: api.addSubscription(label,bmaddressl)'''
            
            unicode(label, 'utf-8')
            address = bitmessagemain.addBMIfNotPresent(address)
            status, addressVersionNumber, streamNumber, toRipe = bitmessagemain.decodeAddress(address)
            if status != 'success':
                raise APIError('Address Error: %s , %s'%(address,status))
            # First we must check to see if the address is already in the
            # subscriptions list.
            queryreturn = bitmessagemain.shared.sqlQuery('''select * from subscriptions where address=?''',address)
            if queryreturn != []:
                raise APIError('AlreadySubscribedError')
            bitmessagemain.shared.sqlExecute('''INSERT INTO subscriptions VALUES (?,?,?)''',label, address, True)
            bitmessagemain.shared.reloadBroadcastSendersForWhichImWatching()

        def addToBlacklist(self, label, address, enabled=True):
            
            '''Add a Bitmessage Address to the Blacklist
            Usage: api.addToBlacklist(label,bmaddress,enabled[True,False])'''
            
            unicode(label, 'utf-8')
            bitmessagemain.shared.sqlExecute('''INSERT INTO blacklist VALUES (?,?,?)''',label,address,enabled)

        def addToWhitelist(self, label, address, enabled=True):
            
            '''Add a Bitmessage Address to the Whitelist
            Usage: api.addToBlacklist(label,bmaddress,enabled[True,False])'''
            
            unicode(label, 'utf-8')
            bitmessagemain.shared.sqlExecute('''INSERT INTO whitelist VALUES (?,?,?)''',label,address,enabled)

        def clientStatus(self):
            
            '''Returns the Status of the Bitmessage Daemon
            Usage: status = api.clinetStatus()
            print status['externalIPAddress']
            print status['networkConnections']
            print status['numberOfMessagesProcessed']
            print status['numberOfBroadcastsProcessed']
            print status['numberOfPubkeysProcessed']
            print status['networkStatus']
            '''
            
            if len(bitmessagemain.shared.connectedHostsList) == 0:
                networkStatus = 'notConnected'
            elif len(bitmessagemain.shared.connectedHostsList) > 0 and not bitmessagemain.shared.clientHasReceivedIncomingConnections:
                networkStatus = 'connectedButHaveNotReceivedIncomingConnections'
            else:
                networkStatus = 'connectedAndReceivingIncomingConnections'
            info = {}
            try:
                info['externalIPAddress'] = bitmessagemain.shared.myExternalIP
            except:
                info['externalIPAddress'] = 'Not implemented jet'
            info['networkConnections'] = len(bitmessagemain.shared.connectedHostsList)
            info['numberOfMessagesProcessed'] = bitmessagemain.shared.numberOfMessagesProcessed
            info['numberOfBroadcastsProcessed'] = bitmessagemain.shared.numberOfBroadcastsProcessed
            info['numberOfPubkeysProcessed'] = bitmessagemain.shared.numberOfPubkeysProcessed
            info['networkStatus'] = networkStatus
            return info

        def createDeterministicAddresses(self,passphrase,label='',numberOfAddresses=1,eighteenByteRipe=False,totalDifficulty=1,smallMessageDifficulty=1,streamNumberForAddress=1,addressVersionNumber=3):
            
            '''Creates a Deterministic Bitmessage Address (an Address based on a password)
            Usage: api.createDeterministicAddresses(passphrase,label,numberOfAddresses,eighteenByteRipe,totalDifficulty,smallMessageDifficulty)'''
            
            if len(passphrase) == 0:
                raise APIError('The specified passphrase is blank.')
            
            if not isinstance(eighteenByteRipe, bool):
                raise APIError('Bool expected in eighteenByteRipe, got %s instead' % type(eighteenByteRipe))
            
            if addressVersionNumber != 3:
                raise APIError('The address version number currently must be 3. Got: %s' % addressVersionNumber)
            
            if streamNumberForAddress != 1:
                raise APIError('Only Stream Number 1 is Supported jet. Got: %s' % streamNumberForAddress)
            
            if numberOfAddresses == 0:
                raise APIError('Why do you want to create 0 Addresses.')
            
            if numberOfAddresses > 999:
                raise APIError('You have (accidentally?) specified too many addresses to make. Maximum 999. \
                This check only exists to prevent mischief; if you really want to create more addresses than this, \
                contact the Bitmessage developers and we can modify the check or you can do it yourself by \
                searching the source code for this message.')

            if not label:
                label = passphrase

            label = unicode(label, 'utf-8')
            nonceTrialsPerByte = int(bitmessagemain.shared.networkDefaultProofOfWorkNonceTrialsPerByte * totalDifficulty)
            payloadLengthExtraBytes = int(bitmessagemain.shared.networkDefaultPayloadLengthExtraBytes * smallMessageDifficulty)
            bitmessagemain.shared.apiAddressGeneratorReturnQueue.queue.clear()
            bitmessagemain.shared.addressGeneratorQueue.put(
                ('createDeterministicAddresses', addressVersionNumber, streamNumberForAddress,
                 label, numberOfAddresses, passphrase, eighteenByteRipe, nonceTrialsPerByte, payloadLengthExtraBytes))
            queueReturn = bitmessagemain.shared.apiAddressGeneratorReturnQueue.get()
            return queueReturn

        def createRandomAddress(self,label,eighteenByteRipe=False,totalDifficulty=1,smallMessageDifficulty=1,streamNumberForAddress=1,addressVersionNumber=3):

            '''Create a reandom Bitmessage Address
            Usage: api.createRandomAddress(label,eighteenByteRipe,totalDifficulty,smallMessageDifficulty)'''

            if not isinstance(eighteenByteRipe, bool):
                raise APIError('Bool expected in eighteenByteRipe, got %s instead' % type(eighteenByteRipe))
            
            if addressVersionNumber != 3:
                raise APIError('The address version number currently must be 3. Got: %s' % addressVersionNumber )
            
            if streamNumberForAddress != 1:
                raise APIError('Only Stream Number 1 is Supported jet. Got: %s' % streamNumberForAddress)
                
            unicode(label, 'utf-8')
            nonceTrialsPerByte = int(bitmessagemain.shared.networkDefaultProofOfWorkNonceTrialsPerByte * totalDifficulty)
            payloadLengthExtraBytes = int(bitmessagemain.shared.networkDefaultPayloadLengthExtraBytes * smallMessageDifficulty)
            bitmessagemain.shared.apiAddressGeneratorReturnQueue.queue.clear()
            bitmessagemain.shared.addressGeneratorQueue.put((
                'createRandomAddress', addressVersionNumber, streamNumberForAddress, label, 1, "", eighteenByteRipe, nonceTrialsPerByte, payloadLengthExtraBytes))
            return bitmessagemain.shared.apiAddressGeneratorReturnQueue.get()

        def deleteAddress(self,address):

            status, addressVersionNumber, streamNumber, toRipe = self._verifyAddress(address)
            address = bitmessagemain.addBMIfNotPresent(address)
            if not bitmessagemain.shared.config.has_section(address):
                raise APIError('Could not find this address in your keys.dat file.')

            bitmessagemain.shared.config.remove_section(address)
            with open(bitmessagemain.shared.appdata + 'keys.dat', 'wb') as configfile:
                bitmessagemain.shared.config.write(configfile)
            
            bitmessagemain.shared.reloadMyAddressHashes()

        def deleteChannel(self,address):
            self.deleteAddress(address)
            self.deleteFromAddressBook(address)

        def deleteFromAddressBook(self,address):

            '''Delete a Contact from Address Book
            Usage: api.deleteContact(bmaddress)'''

            queryreturn = bitmessagemain.shared.sqlExecute('''delete from addressbook where address=?''',address)

        def deleteFromBlacklist(self,address):
            
            '''Delete a Contact from Blacklist
            Usage: api.deleteFromBlacklist(bmaddress)'''
            
            bitmessagemain.shared.sqlExecute('''delete from blacklist where address=?''',address)
            
        def deleteFromWhitelist(self,address):
            
            '''Delete a Contact from Whitelist
            Usage: api.deleteFromWhitelist(bmaddress)'''
            
            bitmessagemain.shared.sqlExecute('''delete from whitelist where address=?''',address)

        def deleteSubscription(self,address):

            '''Delete a Subscription
            Usage: api.deleteSubscription(bmaddress)'''
            
            address = bitmessagemain.addBMIfNotPresent(address)
            bitmessagemain.shared.sqlExecute('''DELETE FROM subscriptions WHERE address=?''',address)
            bitmessagemain.shared.reloadBroadcastSendersForWhichImWatching()

        def getAllInboxMessageIDs(self):
            
            '''Get a List of IDs of all Inbox Messages
            Usage: api.getAllInboxMessageIDs()'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid FROM inbox where folder='inbox' ORDER BY received''')
            data = []
            for msgid in queryreturn:
                data.append(msgid[0].encode('hex'))
            return data
            
        def getAllInboxMessages(self):
            
            '''Return a List of all Inbox Messages
            Usage: api.getAllInboxMessages()'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, received, message, encodingtype, read FROM inbox where folder='inbox' ORDER BY received''')
            messages = []
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, received, message, encodingtype, read = row
                subject = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(subject)
                message = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(message)
                messages.append({'msgid': msgid.encode('hex'),'toAddress': toAddress, 'fromAddress': fromAddress, 'subject': subject, 'message': message, 'encodingType': encodingtype, 'receivedTime': received, 'read': read})
            return messages
            
        def getAllSentMessageIDs(self):
            
            '''Get a List of IDs of all Outbox Messages
            Usage: getAllSentMessageIDs()'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid FROM sent where folder='sent' ORDER BY lastactiontime''')
            data = []
            for row in queryreturn:
                msgid = row[0]
                data.append(msgid.encode('hex'))
            return data
            
        def getAllSentMessages(self):
            
            '''Get a List of all Outbox Messages
            Usage: api.getAllSentMessages()'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, lastactiontime, message, encodingtype, status, ackdata FROM sent where folder='sent' ORDER BY lastactiontime''')
            data = []
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, lastactiontime, message, encodingtype, status, ackdata = row
                subject = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(subject)
                message = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(message)
                data.append({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject, 'message':message, 'encodingType':encodingtype, 'lastActionTime':lastactiontime, 'status':status, 'ackData':ackdata.encode('hex')})
            return data
            
        def getBlackWhitelist(self):
            
            '''Returns the Black- or Whitelist Configuration
            usage: print api.getBlackWhitelist'''
            
            return bitmessagemain.shared.config.get('bitmessagesettings', 'blackwhitelist')
            
        def getDeterministicAddress(self,passphrase):
            
            '''Returns a Deterministic Address for a give Passphrase
            Usage: api.getDeterministicAddress()'''
            
            #hardcoded in correct version and stream number, because they shouldn't be changed until now
            streamNumberForAddress = 1
            addressVersionNumber = 3
            
            numberOfAddresses = 1
            eighteenByteRipe = False
            bitmessagemain.shared.addressGeneratorQueue.put(
                ('getDeterministicAddress', addressVersionNumber,
                 streamNumber, 'unused API address', numberOfAddresses, passphrase, eighteenByteRipe))
            return bitmessagemain.shared.apiAddressGeneratorReturnQueue.get()
            
        def getInboxMessageByID(self, msgid):

            '''Return an Inbox Message by a given ID
            Usage: print api.getInboxMessageByID(MessageID)'''

            msgid = msgid.decode('hex')
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, received, message, encodingtype, read FROM inbox WHERE msgid=?''',msgid)
            data = []
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, received, message, encodingtype, read = row
                subject = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(subject)
                message = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(message)
                data.append({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject, 'message':message, 'encodingType':encodingtype, 'receivedTime':received, 'read': read})
            return data
            
        def getInboxMessagesByReceiver(self,toAddress):
            
            '''Return an Inbox Message by a given Sender Address
            Usage: print api.getInboxMessagesByReceiver(SenderAddress)'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, received, message, encodingtype FROM inbox WHERE folder='inbox' AND toAddress=?''',toAddress)
            data = []
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, received, message, encodingtype = row
                subject = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(subject)
                message = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(message)
                data .append({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject.encode('base64'), 'message':message.encode('base64'), 'encodingType':encodingtype, 'receivedTime':received})
            return data
            
        def getSentMessageByAckData(self,ackData):
            
            '''Return an Inbox Message by a AckData
            Usage: print api.getSentMessageByAckData(AckData)'''
            
            ackData = ackData.decode('hex')
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, lastactiontime, message, encodingtype, status, ackdata FROM sent WHERE ackdata=?''',ackData)
            data = []
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, lastactiontime, message, encodingtype, status, ackdata = row
                subject = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(subject)
                message = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(message)
                data.append({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject, 'message':message, 'encodingType':encodingtype, 'lastActionTime':lastactiontime, 'status':status, 'ackData':ackdata.encode('hex')})
            return data
            
        def getSentMessageByID(self,msgid):

            '''Return an Outbox Message by a given ID
            Usage: print api.getSentMessageByID(MessageID)'''

            msgid = msgid.decode('hex')
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, lastactiontime, message, encodingtype, status, ackdata FROM sent WHERE msgid=?''',msgid)
            data = []
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, lastactiontime, message, encodingtype, status, ackdata = row
                subject = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(subject)
                message = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(message)
                data.append({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject.encode('base64'), 'message':message.encode('base64'), 'encodingType':encodingtype, 'lastActionTime':lastactiontime, 'status':status, 'ackData':ackdata.encode('hex')})
            return data
            
        def getSentMessageStatus(self,ackdata):
            
            '''Returns the Status of an Outbox Message by AckData
            Usage: print api.getSentMessageStatus(AckData)'''

            ackdata = ackdata.decode('hex')
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT status FROM sent where ackdata=?''',ackdata)
            if queryreturn == []:
                return 'notfound'
            for row in queryreturn:
                status, = row
                return status
                
        def getSentMessagesBySender(self, fromAddress):

            '''Return a List of Message by a given Send Address
            Usage: print api.getSentMessagesBySender(SendAddress)'''

            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT msgid, toaddress, fromaddress, subject, lastactiontime, message, encodingtype, status, ackdata FROM sent WHERE folder='sent' AND fromAddress=? ORDER BY lastactiontime''',fromAddress)
            data = []
            for row in queryreturn:
                msgid, toAddress, fromAddress, subject, lastactiontime, message, encodingtype, status, ackdata = row
                subject = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(subject)
                message = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(message)
                data.append({'msgid':msgid.encode('hex'), 'toAddress':toAddress, 'fromAddress':fromAddress, 'subject':subject, 'message':message, 'encodingType':encodingtype, 'lastActionTime':lastactiontime, 'status':status, 'ackData':ackdata.encode('hex')})
            return data
            
        def joinChannel(self, label, testaddress=None):

            '''Join a Channel by a Given Name or Password
            api.joinChannel(label,testaddress[Only for Testing if the Name is correct])'''

            str_chan = '[chan]'
            
            #Precheck Address Book
            queryreturn = bitmessagemain.shared.sqlQuery('''select * from addressbook where label=?''',str_chan + ' ' + label)
            if queryreturn != []:
                raise APIError('Channel already in Addressbook: %s'%label)
            
            #Add Channel to Own Addresses
            bitmessagemain.shared.apiAddressGeneratorReturnQueue.queue.clear()
            bitmessagemain.shared.addressGeneratorQueue.put(('createChan', 3, 1, str_chan + ' ' + label ,label))
            addressGeneratorReturnValue = bitmessagemain.shared.apiAddressGeneratorReturnQueue.get()

            if len(addressGeneratorReturnValue) == 0:
                raise APIError('The Channel is already in use: %s'%label)
                
            address = addressGeneratorReturnValue[0]
            if testaddress:
                if str(address) != str(testaddress):
                    raise APIError('The entered address does not match the address generated by the label')
                    
            #Precheck Address Book
            queryreturn = bitmessagemain.shared.sqlQuery('''select * from addressbook where label=?''',address)
            if queryreturn != []:
                raise APIError('Channel already in Addressbook: %s'%label)
                    
            #Add Address to Address Book
            bitmessagemain.shared.sqlExecute('''INSERT INTO addressbook VALUES (?,?)''',str_chan + ' ' + label, address)
            return address
            
        def listAddresses(self):

            '''List own Addresses
            Usage: print api.listAddresses()'''

            addresses = []
            configSections = bitmessagemain.shared.config.sections()
            for addressInKeysFile in configSections:
                if addressInKeysFile != 'bitmessagesettings':
                    status, addressVersionNumber, streamNumber, hash = bitmessagemain.decodeAddress(addressInKeysFile)
                    addresses.append({'label': bitmessagemain.shared.config.get(addressInKeysFile, 'label'), 'address': addressInKeysFile, 'stream':streamNumber, 'enabled': bitmessagemain.shared.config.getboolean(addressInKeysFile, 'enabled')})
            return addresses
            
        def listBlacklist(self):
            
            '''List all Blacklist Entries
            Usage: print api.listBlacklist()'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''select * from blacklist''')
            data = []
            for row in queryreturn:
                label, address, enabled = row
                label = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(label)
                data.append({'label':label, 'address': address, 'enabled': bool(enabled)})
            return data
            
        def listAddressBook(self):
            
            '''List the Address Book
            Usage: print api.listContacts()'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''select * from addressbook''')
            data = []
            for row in queryreturn:
                label, address = row
                label = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(label)
                data.append({'label':label, 'address': address})
            return data
            
        def listSubscriptions(self):
            
            '''List the all Subscriptions
            Usage: print api.listSubscriptions()'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''SELECT label, address, enabled FROM subscriptions''')
            data = []
            for row in queryreturn:
                label, address, enabled = row
                label = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(label)
                data.append({'label':label, 'address': address, 'enabled': enabled})
            return data
            
        def listWhitelist(self):
            
            '''List all Whitelist Entries
            Usage: print api.listBlacklist()'''
            
            queryreturn = bitmessagemain.shared.sqlQuery('''select * from whitelist''')
            data = []
            for row in queryreturn:
                label, address, enabled = row
                label = bitmessagemain.shared.fixPotentiallyInvalidUTF8Data(label)
                data.append({'label':label, 'address': address, 'enabled': bool(enabled)})
            return data
            
        def markInboxMessageAsRead(self,msgid):
            
            '''Mark an Inbox Message as read
            Usage: api.markInboxMessageAsRead()'''
            
            msgid = msgid.decode('hex')
            bitmessagemain.shared.sqlExecute('''UPDATE inbox SET read='1' WHERE msgid=?''', msgid) 
            
        def markInboxMessageAsUnread(self,msgid):
            
            '''Mark an Inbox Message as unread
            Usage: api.markInboxMessageAsUnread()'''
            
            msgid = msgid.decode('hex')
            bitmessagemain.shared.sqlExecute('''UPDATE inbox SET read='0' WHERE msgid=?''', msgid) 

        def sendBroadcast(self,fromAddress,subject,message):
            
            '''Send a Broadcast to a given Address
            Usage: api.sendBroadcast(BmAddress, Subject, Message)'''
            
            #Hardcoded Encoding Type, no othe supported jet
            encodingType = 2
            
            status, addressVersionNumber, streamNumber, toRipe = bitmessagemain.decodeAddress(fromAddress)
            fromAddress = bitmessagemain.addBMIfNotPresent(fromAddress)
            try:
                fromAddressEnabled = bitmessagemain.shared.config.getboolean(fromAddress, 'enabled')
            except:
                return (fromAddress,'fromAddressNotPresentError')
            if not fromAddressEnabled:
                return (fromAddress,'fromAddressDisabledError')
            ackdata = bitmessagemain.OpenSSL.rand(32)
            toAddress = '[Broadcast subscribers]'
            ripe = ''
            t = ('', toAddress, ripe, fromAddress, subject, message, ackdata, int(
                time.time()), 'broadcastqueued', 1, 1, 'sent', 2)
            bitmessagemain.helper_sent.insert(t)
            toLabel = '[Broadcast subscribers]'
            bitmessagemain.shared.workerQueue.put(('sendbroadcast', ''))
            return ackdata.encode('hex')
            
        def sendMessage(self, fromAddress, toAddress, subject, message):
            
            '''Send a Message to a given Address or Channel
            Usage: api.sendBroadcast(OwnAddress, TargetAddress, Subject, Message)'''
            
            #Hardcoded Encoding Type, no othe supported jet
            encodingType = 2
            
            status, addressVersionNumber, streamNumber, toRipe = bitmessagemain.decodeAddress(toAddress)
            if status != 'success':
                with bitmessagemain.shared.printLock:
                    print 'ToAddress Error: %s , %s'%(toAddress,status)
                return (toAddress,status)
            status, addressVersionNumber, streamNumber, fromRipe = bitmessagemain.decodeAddress(fromAddress)
            if status != 'success':
                with bitmessagemain.shared.printLock:
                    print 'fromAddress Error: %s , %s'%(fromAddress,status)
                return (fromAddress,status)
            toAddress = bitmessagemain.addBMIfNotPresent(toAddress)
            fromAddress = bitmessagemain.addBMIfNotPresent(fromAddress)
            try:
                fromAddressEnabled = bitmessagemain.shared.config.getboolean(fromAddress, 'enabled')
            except:
                return (fromAddress,'fromAddressNotPresentError')
            if not fromAddressEnabled:
                return (fromAddress,'fromAddressDisabledError')
            ackdata = bitmessagemain.OpenSSL.rand(32)
            t = ('', toAddress, toRipe, fromAddress, subject, message, ackdata, int(
                time.time()), 'msgqueued', 1, 1, 'sent', 2)
            bitmessagemain.helper_sent.insert(t)
            toLabel = ''
            queryreturn = bitmessagemain.shared.sqlQuery('''select label from addressbook where address=?''',toAddress)
            if queryreturn != []:
                for row in queryreturn:
                    toLabel, = row
            bitmessagemain.shared.UISignalQueue.put(('displayNewSentMessage', (
                toAddress, toLabel, fromAddress, subject, message, ackdata)))
            bitmessagemain.shared.workerQueue.put(('sendmessage', toAddress))
            return ackdata.encode('hex')
            
        def setBlackWhitelist(self, value):
            
            '''Changes the Settings to Black- or Whitelist
            Usage: api.setBlackWhitelist('black' or 'white')'''
            
            if value not in ['black','white']:
                raise APIError('WrongValueGivenError:%s'%value)

            bitmessagemain.shared.config.set('bitmessagesettings', 'blackwhitelist', value)
            
        def trashInboxMessage(self,msgid):
            
            '''Trash a Message from Inbox by a given ID
            Usage: api.trashInboxMessage(MessageID)'''

            msgid = msgid.decode('hex')
            bitmessagemain.helper_inbox.trash(msgid)

        def trashSentMessage(self,msgid):

            '''Trash a Message from Outbox by a given ID
            Usage: api.trashSentMessage(MessageID)'''

            msgid = msgid.decode('hex')
            bitmessagemain.shared.sqlExecute('''UPDATE sent SET folder='trash' WHERE msgid=?''',msgid)
            
        def _verifyAddress(self, address):
            status, addressVersionNumber, streamNumber, ripe = bitmessagemain.decodeAddress(address)
            if status != 'success':
                logger.warn('API Error 0007: Could not decode address %s. Status: %s.', address, status)

                if status == 'checksumfailed':
                    raise APIError('Checksum failed for address: ' + address)
                if status == 'invalidcharacters':
                    raise APIError('Invalid characters in address: ' + address)
                if status == 'versiontoohigh':
                    raise APIError('Address version number too high (or zero) in address: ' + address)
                raise APIError('Could not decode address: ' + address + ' : ' + status)
            if addressVersionNumber < 2 or addressVersionNumber > 4:
                raise APIError('The address version number currently must be 2, 3 or 4. Others aren\'t supported. Check the address.')
            if streamNumber != 1:
                raise APIError('The stream number must be 1. Others aren\'t supported. Check the address.')

            return (status, addressVersionNumber, streamNumber, ripe)

    api = MainAPI()
    api.start(daemon=True)
    time.sleep(5)
    return api

import unittest
class TestFeed(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print 'Testing PyBitApi, Errors in class_singleWorker.py should be fixed: https://github.com/Bitmessage/PyBitmessage/issues/541'
        global path
        import tempfile
        path = tempfile.mkdtemp()
        
        global api
        api = getAPI(workingdir=path)
        import time
        time.sleep(5)
        
    @classmethod
    def tearDownClass(cls):
        import shutil
        import time
        api.stop()
        time.sleep(10)
        try:
            shutil.rmtree(path)
        except:
            pass
            
    def test_00_delete_standard_subscription(self):
        api.deleteSubscription(api.listSubscriptions()[0]['address'])
        assert len(api.listSubscriptions())==0
        
            
    def test_01_addresses(self):
        api.createRandomAddress('a')
        assert api.listAddresses()[0]['label'] == 'a',api.listAddresses()[0]
        api.createDeterministicAddresses('b')
        assert api.listAddresses()[1]['label'] == 'b',api.listAddresses()[1]
        
        api.deleteAddress(api.listAddresses()[0]['address'])
        api.deleteAddress(api.listAddresses()[0]['address'])
        assert api.listAddresses() == [],api.listAddresses()

    def test_02_subscriptions(self):
        api.addSubscription('a','BM-2D9vJkoGoTBhqMyZyjvELKgBWFMr6iGCQQ')
        assert api.listSubscriptions()[0]['label'] == 'a',api.listSubscriptions()[0]
        api.deleteSubscription(api.listSubscriptions()[0]['address'])
        assert len(api.listSubscriptions()) == 0,api.listSubscriptions()

    def test_03_channels(self):
        api.joinChannel('general')
        assert api.listAddresses()[0]['label'] == '[chan] general',api.listAddresses()[0]
        assert api.listAddressBook()[0]['label'] == '[chan] general',api.listAddressBook()[0]
        api.deleteChannel(api.listAddresses()[0]['address'])
        assert len(api.listAddresses()) == 0 
        assert len(api.listAddressBook()) == 0 
        
    def test_04_manage_addressbook(self):
        api.addToAddressBook('a','a')
        assert api.listAddressBook()[0]['address'] == 'a',api.listContacts()[0]
        count = len(api.listAddressBook())
        api.deleteFromAddressBook('a')
        assert len(api.listAddressBook()) == 0

    def test_05_manage_blackwhitelist(self):
        assert api.getBlackWhitelist() == 'black'
        api.setBlackWhitelist('white')
        assert api.getBlackWhitelist() == 'white'
        api.setBlackWhitelist('black')
        assert api.getBlackWhitelist() == 'black'
        
        api.addToBlacklist('a','a')
        assert api.listBlacklist()[0]['label'] == 'a'
        api.deleteFromBlacklist('a')
        assert api.listBlacklist() == []
        
        api.addToWhitelist('a','a')
        assert api.listWhitelist()[0]['label'] == 'a'
        api.deleteFromWhitelist('a')
        assert api.listWhitelist() == []

    def test_06_send_messages(self):
        addr = api.createRandomAddress('sendtest')
        api.addSubscription('a','BM-2D9vJkoGoTBhqMyZyjvELKgBWFMr6iGCQQ')
        ackdata1 = api.sendMessage(addr,'BM-2D9vJkoGoTBhqMyZyjvELKgBWFMr6iGCQQ','apitest','apitest\nhttps://github.com/merlink01/PyBitAPI')
        ackdata2 = api.sendBroadcast(addr,'apitest','apitest')
        while api.getSentMessageByAckData(ackdata1) == 'notfound':
            pass
        while api.getSentMessageByAckData(ackdata2) == 'notfound':
            pass
            
        assert api.getSentMessageByAckData(ackdata1)[0]['status'] in ['msgqueued', 'broadcastqueued', \
        'broadcastsent', 'doingpubkeypow', 'awaitingpubkey', 'doingmsgpow', 'forcepow', 'msgsent', \
        'msgsentnoackexpected', 'ackreceived'],api.getSentMessageByAckData(ackdata1)
        assert api.getSentMessageByAckData(ackdata2)[0]['status'] in ['msgqueued', 'broadcastqueued', \
        'broadcastsent', 'doingpubkeypow', 'awaitingpubkey', 'doingmsgpow', 'forcepow', 'msgsent', \
        'msgsentnoackexpected', 'ackreceived'],api.getSentMessageByAckData(ackdata2)

    def test_07_manage_sent_messages(self):
        addr = api.createRandomAddress('sendtest')
        ackdata = api.sendMessage(addr,addr,'last','last')
        idnum = api.getSentMessageByAckData(ackdata)[0]['msgid']
        
        assert api.getAllSentMessages() != []
        assert api.getAllSentMessageIDs() != []
        assert api.getSentMessagesBySender(addr) != []
        assert api.getSentMessageByAckData(ackdata) != []
        assert api.getSentMessageByID(idnum) != []
        assert api.getSentMessageStatus(ackdata) in ['msgqueued'],api.getSentMessageStatus(ackdata)

        api.trashSentMessage(idnum)
        messages = api.getAllSentMessages()
        for message in messages:
            assert message['msgid'] != idnum
    
    def test_08_manage_inbox_messages(self):
        assert api.clientStatus > 0, 'Not connected'
        addr = api.createRandomAddress('sendtest')
        counter = 0
        ackdata = api.sendMessage(addr,addr,'test','test')
        while api.getAllInboxMessages() == []:
            if counter > 20:
                ackdata = api.sendMessage(addr,addr,'apitest','apitest\nhttps://github.com/merlink01/PyBitAPI')
            time.sleep(10)
            assert api.clientStatus > 0, 'Not connected'
            
        assert api.getAllInboxMessages() != [],api.getAllInboxMessages()
        assert api.getAllInboxMessageIDs() != [],api.getAllInboxMessageIDs()
        
        msgid = api.getAllInboxMessages()[0]['msgid']
        recv = api.getAllInboxMessages()[0]['toAddress']
        assert api.getInboxMessageByID(msgid) != []
        assert api.getInboxMessagesByReceiver(recv) != []
        
        assert api.getInboxMessageByID(msgid)[0]['read'] == 0,api.getInboxMessageByID(msgid)[0]['read']
        api.markInboxMessageAsRead(msgid)
        assert api.getInboxMessageByID(msgid)[0]['read'] == 1,api.getInboxMessageByID(msgid)[0]['read']
        api.markInboxMessageAsUnread(msgid)
        assert api.getInboxMessageByID(msgid)[0]['read'] == 0,api.getInboxMessageByID(msgid)[0]['read']
        
        api.trashInboxMessage(msgid)
        messages = api.getAllInboxMessages()
        for msg in messages:
            assert msg['msgid'] != msgid
        
        api.getAllInboxMessages()
        
if __name__ == "__main__":
    import logging,os,sys
    logger = logging.getLogger()
    fmt_string = "[%(levelname)-7s]%(asctime)s.%(msecs)-3d\
    %(module)s[%(lineno)-3d]/%(funcName)-10s  %(message)-8s "
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt_string, "%H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    
    unittest.main()
