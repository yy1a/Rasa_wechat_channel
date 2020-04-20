# Building WeChat Channel for Rasa


## Package requirement:
1. Python 3.7.3 (3.7.7 is not recommended)
2. Tensorflow 2
4. Rasa -- pip3 install rasa


## Instructions for deployment: 

1. Follow the instructions on 'https://developers.weixin.qq.com/doc/offiaccount/Getting_Started/Getting_Started_Guide.html' to setup your account. Insert your callback URL which will look like ```https://<YOUR_HOST>/webhooks/wechat/webhook```

3. Use default model from rasa for test; Run 'rasa init --no-prompt'.

4. Create a credentials_wc.yml, and enter information as below:
```
wechat:
  appid: "APPID"
  verify: "Token"
  secret: "Appsecret"
  customer_mode: True if your account is verified else False
```

5. Run 'nohup rasa run --credentials credentials_wc.yml &'

6. Now you can start chatting with rasa on your WeChat account.
