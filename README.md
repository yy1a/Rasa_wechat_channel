Building WeChat Channel for Rasa


Package requirement:
1. Python 3.7.3 (3.7.7 is not recommended)
2. Tensorflow 2
4. Rasa -- pip3 install rasa


Instructions for deployment: 

1. Follow the instructions on 'https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Getting_Started_Guide.html' to setup your account. Insert your callback URL which will look like https://<YOUR_HOST>/webhooks/wechat/webhook

2. If your account is verified, skip this step. Updating your Rasa server IP address in rasa/core/channels/wechat_utils/rasa_server.py, 'connection = http.client.HTTPConnection('Rasa server IP address at port 80')'. Your rasa server IP address can be found after you run 'rasa run' in terminal.

3. Use default model from rasa for test; Run 'rasa init --no-prompt'.

4. Create a credentials_wc.yml, and enter information as below:

wechat:
  verify: "token of your account"\n
  secret: "AppSecret of your account"\n
  customer_mode: True if your account is verified else False\n


5. If your account is verified, skip this step. Otherwise, run 'nohup rasa run -p 80 &'

6. Run 'nohup rasa run --credentials credentials_wc.yml &'

5. Now you can start chatting with rasa on your WeChat account.
