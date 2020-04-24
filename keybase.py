import weechat
import subprocess
import json
import socket 

def private_input_cb(data, buffer, input_data):
    ## I need to echo out the data
    global status
    api = {"method": "send", "params": {"options": {"conversation_id": data, "message": {"body": input_data}}}}
    #echo = status.nick_name+'\t'+input_data
    #weechat.prnt_date_tags(buffer, 0, "", echo) 
    ## And then, i need to send it
    r=status.execute_api(api)
    ## CHECK r. Moreover, we can trigger the execution in another thread
    return weechat.WEECHAT_RC_OK

def private_close_cb(data, buffer):
    global server
    del status.private_chans[data]
    return weechat.WEECHAT_RC_OK
## Todo wrapper 
def status_input_cb(data, buffer, input_data):
    weechat.prnt("", str(data) + str(input_data))
    return weechat.WEECHAT_RC_OK

def status_close_cb(data, buffer):
    weechat.prnt("", str(data))
    return weechat.WEECHAT_RC_OK

def start_reading(data, command, return_code, out, err):
    #weechat.prnt("","Command:"+str(command))
    ## Maybe we can check this to see if the program is crashed
    #weechat.prnt("","return_code:"+str(return_code))
    weechat.prnt("","out:"+str(out))
    if out == "":
        return weechat.WEECHAT_RC_OK
    j = json.loads(out)
    id = j['msg']['conversation_id']
    date,body,n = handle_message(j['msg'])
    global status
    if id not in status.private_chans:
        status.open_conv_id(j['msg'])
    username = body.split('/t')
    priority = "notify_private"
    if len(username) == 2:
        if status.nick_name in username[1]:
            priority = "notify_highlight"
    weechat.prnt_date_tags(status.private_chans[id], date,priority, body)
    #notify_none Buffer with line is not added to hotlist.
    #notify_message Buffer with line is added to hotlist with level "message".
    #notify_private Buffer with line is added to hotlist with level "private".
    #notify_highlight Buffer with line is added to hotlist with level "highlight". 
    #weechat.prnt("","err:"+str(err))
    return weechat.WEECHAT_RC_OK

def handle_message(msg):
    sender = msg['sender']['username']
    date = msg['sent_at']
    content = msg['content']['type']
    if content == 'join':
        body = weechat.prefix ("join")+sender+" has joined the channel"
    elif 'text' in msg['content']:
        body = sender+'\t'+msg['content']['text']['body']
    else:
        body = str(msg)
    n    = int(msg['id'])
    return date,body,n
 
class status_server:
    def __init__(self):
        self.status_name = "keybase"
        self.nick_name   = "c3r34lk1ll3r"
        self.private_chans = {}
        #self.team_chans    = {}
        self.status = weechat.buffer_new(self.status_name, "status_input_cb", "", "status_close_cb", "")
        weechat.buffer_set(self.status, "localvar_set_type", "server")
        weechat.buffer_set(self.status, "localvar_set_server", "keybase")
        self.init_chats()
        self.get_history()
        weechat.prnt("", "readed history")
        self.reader = weechat.hook_process_hashtable("keybase chat api-listen",
                                                    {"buffer_flush":"1"},0,"start_reading","")
    def execute_api(self, api):
        output = subprocess.check_output(['keybase', 'chat', 'api', '-m', json.dumps(api)])
        #weechat.prnt("", "D "+str(output))
        j = json.loads(output)
        if 'error' in j:
            weechat.prnt_date_tags(self.status, 0, "", weechat.prefix("error")+"[X] Error during API "+str(api))
            weechat.prnt(self.status, "Debug: "+str(api))
            return None
        result = json.loads(output)['result']
        return result

    def get_history(self, conv_id = []):
        api = {"method": "read", "params": {"options": {"conversation_id": "" }}}
        if len(conv_id) == 0:
            conv_id = self.private_chans
        for id in conv_id:
            api['params']['options']['conversation_id']=id
            result = self.execute_api(api)
            weechat.prnt(self.status, "History: "+str(result))
            num = int(result['pagination']['num'])
            mss = [None] * (num+1)
            for i in result['messages']:
                date, body, n = handle_message(i['msg'])
                weechat.prnt("", str(mss))
                mss[n] = [date, body]
            i = 0
            while i <= num:
                msg = mss[i]
                if msg != None:
                    weechat.prnt_date_tags(self.private_chans[id], msg[0],"", msg[1])
                i+=1
    def open_conv_id(self,msg):
        conv_id = msg['conversaion_id']
        buff = self.create_new_buffer(msg, conv_id)
        self.private_chans[conv_id] = buff
        self.get_history(conv_id=[conv_id])

    def init_chats(self):
        api = {"method":"list"}
        results=self.execute_api(api)
        chats  = results['conversations']
        for chat in chats:
            buff = self.create_new_buffer(chat, chat['id'])
            self.private_chans[chat['id']] = buff
            #name = chat['channel']['name']
            #id   = chat['id']
            #if self.nick_name in name:
            #    ## Private conversation
            #    if len(name.split(',')) == 1:
            #        b_name = name
            #    else:
            #        b_name = ",".join(name.split(',')[1:])
            #    buff = weechat.buffer_new(b_name, "private_input_cb", id, "private_close_cb", id)
            #    self.private_chans[id] = buff
            #    weechat.buffer_set(buff, "localvar_set_type", "private")
            #    weechat.buffer_set(buff, "localvar_set_server", "keybase")
            #    ## We will change this later TODO backlog
            #    weechat.buffer_set(buff, "localvar_set_no_log", "1")
            #    weechat.prnt(self.status, "Created new private channel between \'"+self.nick_name +"\' and \'"+b_name+"\'") 
            #else:
            #    #if name not in self.team_chans:
            #    #    weechat.prnt(self.status, "New team detected: create a status_buffer for " +name)
            #    #    team_buf = weechat.buffer_new(name, "chan_input_cb", "", "chan_close_cb", "")
            #    #    self.team_chans[name] = [team_buf]
            #    #    weechat.buffer_set(team_buf, "localvar_set_type", "server")
            #    #    weechat.buffer_set(team_buf, "localvar_set_server", name)
            #    t_name = chat['channel']['topic_name']
            #    buff = weechat.buffer_new(name+'#'+t_name, "private_input_cb", id, "private_close_cb", id)
            #    self.private_chans[id] = buff
            #    weechat.buffer_set(buff, "localvar_set_type", "private")
            #    weechat.buffer_set(buff, "localvar_set_server", "keybase")
            #    weechat.buffer_set(buff, "localvar_set_no_log", "1")
            ##weechat.hook_signal_send("logger_backlog", weechat.WEECHAT_HOOK_SIGNAL_POINTER, buff)
    def create_new_buffer(self, msg, conv_id):
        channel = msg['channel']
        name = channel['name']

        if channel['members_type'] == 'impteamnative':
            ## We don't want to replicate our username
            name_splitted = name.split(',')
            ## We can send message to ourself
            if len(name_splitted) == 1:
                buff_name = name
            else:
                buff_name = ",".join(name_splitted[1:])
        elif channel['members_type'] == 'team':
            buff_name = "#"+channel['topic_name']
        else:
            buff_name ="BOH!"+channel['member_type']
        buff = weechat.buffer_new(buff_name, "private_input_cb", conv_id, "private_close_cb", conv_id)
        weechat.buffer_set(buff, "localvar_set_type", "private")
        weechat.buffer_set(buff, "localvar_set_server", "keybase")
        weechat.buffer_set(buff, "localvar_set_no_log", "1")         
        weechat.buffer_set(buff, "unread", "")
        weechat.buffer_set(buff, "notify", "3")
        return buff 
# =================================[ Main ]================================== {{{
if __name__ == "__main__":
    weechat.register("keybase", "c3r34lk1ll3r", "0.0", "GPL3", "Keybase plugin", "", "")
    global status 
    status = status_server()
# }}} 
