import weechat
import subprocess
import json
import socket 
import tempfile


# =================================[ Callback functions ]================================== {{{

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
    if debug:
        body = weechat.color('/darkgray')+"DEBUG\t"+weechat.color('/darkgray')+str(j)
        weechat.prnt_date_tags(status.private_chans[id], date,"notify_none", body)
    #notify_none Buffer with line is not added to hotlist.
    #notify_message Buffer with line is added to hotlist with level "message".
    #notify_private Buffer with line is added to hotlist with level "private".
    #notify_highlight Buffer with line is added to hotlist with level "highlight". 
    #weechat.prnt("","err:"+str(err))
    return weechat.WEECHAT_RC_OK

def handle_system_message(msg):
    system = msg['content']['system']
    body = weechat.color("/cyan")+"SYSTEM\t"
    if system['systemType'] == 0:
        ## someone added someone to chat
        addedtoteam = system['addedtoteam']
        adder = addedtoteam['adder']
        addee = addedtoteam['addee']
        role  = addedtoteam['role']
        bulkAdds = addedtoteam['bulkAdds']
        body = weechat.color("/cyan")+adder+" added \'"+addee+"\' to team with role "+str(role)
    elif system['systemType'] == 7:
        ## Bulk add
        bulkaddtoconv = system['bulkaddtoconv']
        username = bulkaddtoconv['usernames']
        users = (",").join(username[:])
        body = weechat.prefix("join") +users+ " have joined the channel" 
    elif system['systemType'] == 9:
        ## Creation of a new channel
        new_channel = system['newchannel']
        creator = new_channel['creator']
        name_channel = new_channel['nameAtCreation']
        body+=weechat.color("/cyan")+creator+" created \'"+name_channel+"\' channel"
    else:
        body+=weechat.color("red")+"type not supported. Raw message:"+str(msg)
    return body

def add_reaction(msg, buffer):
    #hdata = weechat.hdata_get("b
    pass

#    {"method": "mark", "params": {"options": {"channel": {"name": "you,them"}, "message_id": 72}}} mark the message read.. we can use when we switch buffer
# If it from history we can skip the delete and modify messages
def handle_message(msg):
    sender = msg['sender']['username']
    date = msg['sent_at']
    content = msg['content']['type']
    id = msg['id']
    sender = sender+weechat.color("/lightmagenta")+" ["+str(id)+"]"
    if content == 'join':
        body = weechat.prefix("join")+sender+" has joined the channel"
    elif content == 'system':
        body = handle_system_message(msg)
    elif content == 'text':
        text = msg['content']['text']
        msg_body = text['body'].replace('\t',"    ")
        ## Mention username
        user_mention =  text['userMentions']
        if user_mention != None:
            for user in user_mention:
                msg_body = msg_body.replace('@'+user['text'],weechat.color("*red")+'@'+user['text']+weechat.color("reset"))
                #if user['text'] == self.nick --> PRIORITY
        body = sender+'\t'+msg_body
    #elif content == 'unfurl':
    #    body = sender+'\t'+
    elif content == 'delete':
        body = sender+'\t'+weechat.color("*red")+"deleted message(s) "+str(msg['content']['delete']['messageIDs'])
    elif content == 'edit':
        edit = msg['content']['edit']
        body = sender+'\t'+weechat.color("*red")+"edit message "+str(edit['messageID'])+" with:"+edit['body']
    elif content == 'metadata':
        body = sender+'\t'+"Metadata: Conversation Title: "+msg['content']['metadata']['conversationTitle']
    elif content == 'attachment':
        body = sender+"\t"+weechat.color("_lightgreen")+"sent an attachment. Use /download "+str(id)+" <output>"
    else:
        body = weechat.color("*red")+str(msg)
    n    = int(msg['id'])
    return date,body,n

def open_attachment(data, buffer, arg):
    if arg == "":
        return weechat.WEECHAT_RC_ERROR
    conv_id = weechat.buffer_get_string(buffer, "localvar_conversation_id")
    tmp_file = tempfile.mkstemp(suffix = '.ktmp')
    weechat.prnt("", str(tmp_file))
    api = {"method": "download", "params": {"options": {"conversation_id": conv_id, "message_id": int(arg), "output": tmp_file[1]}}}
    ## CHECK r
    r=status.execute_api(api)
    subprocess.Popen(['xdg-open',tmp_file[1]],close_fds=True)
    return weechat.WEECHAT_RC_OK


def download_message(data, buffer, arg):
    args = arg.split(' ')
    if len(args) != 2:
        return weechat.WEECHAT_RC_ERROR
    conv_id = weechat.buffer_get_string(buffer, "localvar_conversation_id")
    api = {"method": "download", "params": {"options": {"conversation_id": conv_id, "message_id": int(args[0]), "output": args[1]}}}
    ## CHECK r
    r=status.execute_api(api)
    return weechat.WEECHAT_RC_OK

# {"method": "send", "params": {"options": {"channel": {"name": "you,them"}, "message": {"body": "is it cold today?"}}}}
def send_new_message(data, buffer, command):
    args = command.split(' ')
    weechat.prnt("", str(args))
    if len(args) < 3:
        return weechat.WEECHAT_RC_ERROR
    receiver = args[1]
    body = "".join(args[2:])
    api = {"method": "send", "params": {"options": {"channel": {"name": status.nick_name+','+receiver}, "message": {"body": body}}}}
    r = status.execute_api(api)
    ## I should also search the right buffer but I receive the message so the buffer is created after
    return weechat.WEECHAT_RC_OK_EAT

# }}}

# =================================[ Server connection ]================================== {{{

class status_server:
    def __init__(self, options):
        self.status_name = options['server_name']
        self.nick_name   = options['nickname']
        global debug
        debug = options['debug']
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
        weechat.hook_command("download", "Download an attachment", "<msg_id> <outputh_path>", "<msg_id>: ID of the message\n<output_path>: Path to store file", "", "download_message", "") 
        weechat.hook_command("open", "Open (with default application) an attachment", "<msg_id>", "<msg_id>: ID of the message\n", "", "open_attachment", "") 
        ## Hooking to classic weechat command
        weechat.hook_command_run("/msg","send_new_message","") 
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
            #weechat.prnt(self.status, "History: "+str(result))
            num = int(result['pagination']['num'])
            mss = [None] * (num+1)
            for i in result['messages']:
                date, body, n = handle_message(i['msg'])
                mss[n] = [date, body, i]
            i = 0
            while i <= num:
                msg = mss[i]
                if msg != None:
                    weechat.prnt_date_tags(self.private_chans[id], msg[0],"", msg[1])
                    if debug:
                        body = weechat.color('/darkgray')+"DEBUG\t"+weechat.color('/darkgray')+str(msg[2])
                        weechat.prnt_date_tags(self.private_chans[id], msg[0],"notify_none", body)
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
        weechat.buffer_set(buff, "localvar_set_conversation_id", conv_id)
        weechat.buffer_set(buff, "unread", "")
        weechat.buffer_set(buff, "notify", "3")
        return buff 
# }}}

# =================================[ Main ]================================== {{{
if __name__ == "__main__":
    weechat.register("weebase", "c3r34lk1ll3r", "0.0", "GPL3", "Keybase plugin", "", "")
    script_options = {
    "nickname": "",
    "debug": "False",
    "server_name": "KeyBase",
    }
    for option, default_value in script_options.items():
        if not weechat.config_is_set_plugin(option):
            weechat.config_set_plugin(option, default_value)
    PREFIX = "plugins.var.python.weebase."
    script_options['nickname'] = weechat.config_string(weechat.config_get(PREFIX+"nickname"))
    script_options['server_name'] = weechat.config_string(weechat.config_get(PREFIX+"server_name"))
    script_options['debug'] = weechat.config_boolean(weechat.config_get(PREFIX+"debug"))
    global status 
    weechat.prnt("", script_options['nickname'])
    if script_options['nickname'] == "":
        weechat.prnt("", weechat.prefix("error")+"you should set nickname first!")    
    else:
        status = status_server(script_options)
# }}} 
