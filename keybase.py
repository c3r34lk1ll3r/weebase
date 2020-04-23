import weechat
import subprocess
import json
import socket 

def private_input_cb(data, buffer, input_data):
    ## I need to echo out the data
    global status
    api = {"method": "send", "params": {"options": {"conversation_id": data, "message": {"body": input_data}}}}
    echo = status.nick_name+'\t'+input_data
    weechat.prnt_date_tags(buffer, 0, "", echo) 
    ## And then, i need to send it
    status.execute_api(api)
    return weechat.WEECHAT_RC_OK

def private_close_cb(data, buffer):
    ## I need to delete the key from the dictionary
    return weechat.WEECHAT_RC_OK

## THIS IS ALL TODO
def team_input_cb(data, buffer, input_data):
    weechat.prnt("", str(data) + str(input_data))
    return weechat.WEECHAT_RC_OK

def team_close_cb(data, buffer):
    weechat.prnt("", str(data))
    return weechat.WEECHAT_RC_OK

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
    msg = j['msg']
    id = msg['conversation_id']
    date = msg['sent_at']
    try:
        body = msg['sender']['username'] + '\t'+ msg['content']['text']['body']
    except Exception as e:
        body = str(msg)
    global status
    if id in status.private_chans:
        weechat.prnt_date_tags(status.private_chans[id], date,"", body)
    #weechat.prnt("","err:"+str(err))
    return weechat.WEECHAT_RC_OK

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
        ## Create tunnel for reading data
        #self.hook = weechat.hook_process("func:start_reading", 0, "start_reading_cb", "")
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

    def get_history(self):
        api = {"method": "read", "params": {"options": {"conversation_id": "" }}}
        for id in self.private_chans:
            api['params']['options']['conversation_id']=id
            result = self.execute_api(api)
            weechat.prnt(self.status, "History: "+str(result))
            num = int(result['pagination']['num'])
            mss = [None] * (num+1)
            for i in result['messages']:
                msg = i['msg']
                sender = msg['sender']['username']
                date = msg['sent_at']
                if 'text' in msg['content']:
                    body = sender+'\t'+msg['content']['text']['body']
                else:
                    body = str(msg['content'])
                n    = int(msg['id'])
                mss[n] = [date, body]
                weechat.prnt("", str(mss))
            i = 2
            while i <= num:
                msg = mss[i]
                if msg != None:
                    weechat.prnt_date_tags(self.private_chans[id], msg[0],"", msg[1])
                i+=1
            
    def init_chats(self):
        api = {"method":"list"}
        results=self.execute_api(api)
        chats  = results['conversations']
        for chat in chats:
            name = chat['channel']['name']
            id   = chat['id']
            if self.nick_name in name:
                ## Private conversation
                if len(name.split(',')) == 1:
                    b_name = name
                else:
                    b_name = ",".join(name.split(',')[1:])
                buff = weechat.buffer_new(b_name, "private_input_cb", id, "private_close_cb", id)
                self.private_chans[id] = buff
                weechat.buffer_set(buff, "localvar_set_type", "private")
                weechat.buffer_set(buff, "localvar_set_server", "keybase")
                ## We will change this later TODO backlog
                weechat.buffer_set(buff, "localvar_set_no_log", "1")
                weechat.prnt(self.status, "Created new private channel between \'"+self.nick_name +"\' and \'"+b_name+"\'") 
            else:
                #if name not in self.team_chans:
                #    weechat.prnt(self.status, "New team detected: create a status_buffer for " +name)
                #    team_buf = weechat.buffer_new(name, "chan_input_cb", "", "chan_close_cb", "")
                #    self.team_chans[name] = [team_buf]
                #    weechat.buffer_set(team_buf, "localvar_set_type", "server")
                #    weechat.buffer_set(team_buf, "localvar_set_server", name)
                t_name = chat['channel']['topic_name']
                buff = weechat.buffer_new(name+'#'+t_name, "private_input_cb", id, "private_close_cb", id)
                self.private_chans[id] = buff
                weechat.buffer_set(buff, "localvar_set_type", "private")
                weechat.buffer_set(buff, "localvar_set_server", "keybase")
                weechat.buffer_set(buff, "localvar_set_no_log", "1")
            #weechat.hook_signal_send("logger_backlog", weechat.WEECHAT_HOOK_SIGNAL_POINTER, buff)

# =================================[ Main ]================================== {{{
if __name__ == "__main__":
    weechat.register("keybase", "c3r34lk1ll3r", "0.0", "GPL3", "Keybase plugin", "", "")
    global status 
    status = status_server()
# }}} 
