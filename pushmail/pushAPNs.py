#!/usr/bin/env python

import sys, os, time, json, re
import traceback
sys.path.append(os.path.abspath('/etc/postfix/pushmail/lib'))
from mailparser import MailParser
import email.utils
from apns import APNs, Frame, Payload
import mysql.connector
from mysql.connector import MySQLConnection, Error

import logging
logging.basicConfig(filename='/etc/postfix/pushmail/pushmail.log', level=logging.WARNING, 
                    format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger=logging.getLogger(__name__)

def get_device_id(email):
	 try:
	 	conn = mysql.connector.connect(host='xxx',database='xxx',user='xxx',password='xxx')
	 	cursor = conn.cursor()
	 	#emails = "9999demoflo@exemple"
	 	query = ("SELECT device_token FROM device_token dvleft JOIN users u ON u.id = user_id WHERE u.email = '%s' LIMIT 0 , 30" %(email))
	 	cursor.execute(query)
	 	rows = cursor.fetchall()
	 	return rows

	 except Error as e:
	 	#print(e)
		logger.error(e)

	 finally:
	  cursor.close()
	  conn.close()


if __name__ == "__main__":
    try:
        content = sys.stdin.read()
        parser = MailParser()
        parser.parse_from_string(content)
    except:
        logger.error(traceback.format_exc())
        sys.exit()

    data = {}
    sfrom = email.utils.parseaddr(parser.from_)
    ssubject = parser.subject

    if sfrom[0]:
    	sfrom = sfrom[0]
        
        if '=?utf-8?' in sfrom or '=?UTF-8?' in sfrom:
            sfrom = email.Header.decode_header(sfrom)[0][0]
    else:
        sfrom = sfrom[1]

    if '=?utf-8?' in ssubject or '=?UTF-8?' in ssubject:
        if ssubject.startswith('"') and ssubject.endswith('"'):
             ssubject = ssubject[1:-1]
        if ssubject.startswith('\'') and ssubject.endswith('\''):
             ssubject = ssubject[1:-1]

        if isinstance(ssubject, unicode):
            ssubject = ssubject.encode('utf-8')

        try:
            ssubject = email.Header.decode_header(ssubject)[0][0]
        except Exception, e:
            logger.error(traceback.format_exc())

    if isinstance(sfrom, unicode):
        sfrom = sfrom.encode('utf-8')

    if isinstance(ssubject, unicode):
        ssubject = ssubject.encode('utf-8')


    data['body'] = sfrom + "\n" + ssubject[:128] + "\n"

    # check X-Original-To header to get destination email
    match = re.findall(r'X-Original-To [\w\.-]+@[\w\.-]+', parser.headers)
    if match:
        match2 = re.findall(r'[\w\.-]+@[\w\.-]+', match[0])
        data['email'] = match2[0]
    else:
        data['email'] = ''

    data['messageID'] = ''
    if parser.message_id:
        data['messageID'] = re.sub('[<>]', '', parser.message_id)


    data['folder'] = 'INBOX'

    # Convert data to json
    json_data = json.dumps(data)
    json_mess = json.loads(json_data)
 
    apns = APNs(use_sandbox=False, cert_file='/etc/postfix/pushmail/key.pem', key_file='/etc/postfix/pushmail/key.pem')
    apns_enhanced = APNs(use_sandbox=False, cert_file='/etc/postfix/pushmail/key.pem', enhanced=True)
    payload = Payload(alert= json_mess , sound="default", badge=1)

    # Send a notification
    if data['email']:
    	device_id_list = get_device_id(data['email'])
    #	frame = Frame()
    #	identifier = 1
    #	expiry = time.time()+3600
    #	priority = 10
	if len(device_id_list) > 1:
            timeout = 1
        else:
            timeout = 0

    	for i in  device_id_list:
    		token_hex = i[0]
    		apns_enhanced.gateway_server.send_notification(token_hex, payload)
		apns_enhanced.gateway_server.force_close()
		time.sleep(timeout)
    	
    else:
    	print "No X-Original-To Header"
    sys.exit()
