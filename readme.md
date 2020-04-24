⚠️ *_In heavy development. No support provided. There is an high change that this will crash weechat and/or it doesn't work_* ⚠️

# Wee_keybase
Plugin for integrate _keybase_ in _weechat_.

## Installation
Copy the python file in weechat plugin folder (for example `~/.weechat/python/`) and load it from weechat (`/python load keybase.py`)

## Requirements
- `kebase`: This plugin is simply a wrapper for `keybase` CLI.

## Modification
You should modify the plugin code in order to set your `nickname`. 
```
self.nick_name = <YOUR NICK HERE>
```

