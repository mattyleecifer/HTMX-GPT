from flask import Flask, session, redirect, render_template, request, flash, jsonify, send_file, render_template_string
import openai, json, secrets, os

app = Flask(__name__)

app.secret_key = secrets.token_hex(16)

def getresponse(messages):
    res = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=messages
    )
    return res

def getChat(tokencount, messages, text):
    if not text:
        return tokencount, messages
    messages.append({"role": "user", "content": text})
    response = getresponse(messages)
    tokens = response['usage']['total_tokens']
    tokencount = tokencount + tokens
    response = response['choices'][0]['message']
    messages.append(response)
    return tokencount, messages

@app.route('/')
def home():
    # validate key
    if 'key' not in session:
        if os.path.exists(os.path.join(os.getcwd(), "apikey.txt")):
        #     with open("apikey.txt", 'r') as file:
        #         key = file.read()
        #     session['key'] = key
        #     openai.api_key = key
        #     if not key or not key.startswith('sk-'):
        #         return redirect('/key')
        # else:
            return redirect('/key')
    if 'default' not in session:
        session['default'] = "You are a helpful assistant. Please generate truthful, accurate, and honest responses while also keeping your answers succinct and to-the-point."
    if 'messages' not in session:
        session['messages'] = [{"role": "system", "content": session.get('default')}]
    if 'tokencount' not in session:
        session['tokencount'] = 0
    if 'savedchats' not in session:
        session['savedchats'] = []
    return render_template("chat.html")

@app.route('/key')
def savekeypage():
    return render_template("savekey.html")

@app.route('/clearkey', methods=['POST'])
def clearkey():
    return render_template_string('<input name="key" id="key" value="" autocomplete="off">')

@app.route('/savekey', methods=['POST'])
def savekey():
    key = request.form['key']
    if not key.startswith('sk-'):
        return redirect('/key')
    openai.api_key = key
    # with open('apikey.txt', mode='w') as file:
    #     file.write(key)
    session['key'] = key
    return redirect('/')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        session['tokencount'], session['messages'] = getChat(session.get('tokencount'), session.get('messages'), session.get('text'))
        message = session.get('messages')[-1]['content']
        message = message.split('\n')
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        message = "Error: " + error_type + " : " + error_message
        message = message.split('\n')
    return render_template("newchat.html", agent=session.get('messages')[-1]['role'], message=message, messageid=len(session.get('messages')) - 1)


@app.route('/submit', methods=['POST'])
def submit():
    text = session.get('text')
    text = text.split('\n')
    return render_template("usermessage.html", usertext=text, messageid=len(session.get('messages')))

@app.route('/clearchat', methods=['POST'])
def clearchat():
    session['text'] = request.form['text']
    print(session.get('text'))
    return render_template("inputbox.html")

@app.route('/reset', methods=['POST'])
def reset():
    session['messages'] = [{"role": "system", "content": session.get('default')}]
    session['tokencount'] = 0
    return render_template("blankchat.html")

@app.route('/newsession', methods=['GET'])
def newsession():
    session.clear()
    session['default'] = "You are a helpful assistant. Please generate truthful, accurate, and honest responses while also keeping your answers succinct and to-the-point."
    session['messages'] = [{"role": "system", "content": session.get('default')}]
    session['tokencount'] = 0
    session['savedchats'] = []
    messagelist = '<table><tr id="chattext"><td><div id="centertext" hx-get="/tokenupdate" hx-trigger="load" hx-target="#tokens" hx-swap="innerHTML">Start asking questions!</div></td></tr></table>'
    return render_template_string(messagelist)

@app.route('/scroll', methods=['GET'])
def scroll():
    return ""

@app.route('/edit', methods=['GET'])
def edit():
    messageid = request.args.get('messageid')
    print(messageid)
    edittext = session.get('messages')[int(messageid)]['content']
    return render_template("edit.html", edittext=edittext, messageid=messageid)

@app.route('/edit', methods=['POST'])
def edited():
    messageid = int(request.form['messageid'])
    edittext = request.form['edittext']
    messages = session.get('messages')
    messages[messageid]['content'] = edittext
    session['messages'] = messages
    edittext = edittext.split('\n')
    return render_template("edited.html", edittext=edittext, messageid=messageid)

@app.route('/save', methods=['POST'])
def save():
    savedchats = session.get('savedchats')
    messages = session.get('messages')
    savedchats.append(messages)
    session['savedchats'] = savedchats
    chatid = len(savedchats) - 1
    title = messages[1]['content'][0:20]
    data = str(messages)
    return render_template("save.html", chatid=chatid, title=title, data=data)

@app.route('/load', methods=['POST'])
def load():
    data = request.form['data']
    # print(data)
    # data = data.replace("%20", " ")
    # data = data.replace("\\n", "\n")
    data = data.replace("'", '"')

    print(data)
    data = json.loads(data)
    session['messages'] = data
    return loadmessages()

@app.route('/delete', methods=['POST'])
def delete():
    messageid = int(request.form['messageid'])
    messages = session.get('messages')
    messages[messageid]['content'] = " "
    session['messages'] = messages
    return render_template_string("")

@app.route('/deletechathistory', methods=['POST'])
def deletechathistory():
    chatid = int(request.form['chatid'])
    savedchats = session.get('savedchats')
    savedchats[chatid] = ""
    session['savedchats'] = savedchats
    return render_template_string("")


@app.route('/tokenupdate', methods=['GET'])
def tokenupdate():
    tokencount = session.get('tokencount')
    estcost = tokencount/1000
    estcost *= 0.002
    estcost = round(estcost, 5)
    print(estcost)
    return render_template("tokencount.html", tokencount=tokencount, estcost=estcost)

@app.route('/getchathistory', methods=['GET'])
def getchathistory():
    savedchats = session.get('savedchats')
    if not savedchats:
        html = '<div id="addchat"></div>'
    else:
        html = ''
        for i in range(0, len(savedchats)):
            if not savedchats[i]:
                continue
            html += '<div class="savedchat" id="savedchat' + str(i) + '"><div>'
            html += savedchats[i][1]['content'][:20]
            html += '</div><div><form hx-post="/load" hx-target="#top-row" hx-swap="innerHTML"><input type="hidden" name="data" value="' + str(savedchats[i]) + '"><button class="btn">Load</button></form><form hx-post="/deletechathistory" hx-target="#savedchat' + str(i) + '" hx-swap="outerHTML"><input type="hidden" name="chatid" value="' + str(i) + '"><button class="btn">Delete</button></form></div></div>'
        html += '<div id="addchat"></div>'
    return render_template_string(html)

@app.route('/loadmessages', methods=['GET'])
def loadmessages():
    messages = session.get('messages')
    if len(messages) == 1:
        messagelist = '<table><tr id="chattext"><td><div id="centertext" hx-get="/tokenupdate" hx-trigger="load" hx-target="#tokens" hx-swap="innerHTML">Start asking questions!</div></td></tr></table>'
    else:
        messagelist = '<table>'
        for i in range(len(messages)):
            if messages[i]['content'] == " ":
                continue
            if messages[i]['role'] == 'user':
                messagelist += '''<tr style="display: inline-block;"><td>
        <div class="agent">User</div>
      </td>
      <td id="reply-''' + str(i) + '''">
        <div class="message" messageid="''' + str(i) +'''" style="float: left;">'''
                lines = messages[i]['content'].split('\n')
                for j in lines:
                    messagelist += j + '<br>'

                messagelist += '''<br>
        <div class="editbutton" style="float: right;">
            <form hx-get="/edit" hx-target="#reply-''' + str(i) + '''" hx-swap="outerHTML">
                <input type="hidden" name="messageid" value="''' + str(i) + '''">
                <button class="btn">Edit</button>
            </form>
            <form hx-post="/delete" hx-target="closest tr" hx-swap="outerHTML">
                <input type="hidden" name="messageid" value="''' + str(i) + '''">
                <button class="btn">Delete</button>
            </form>
        </div>
      </td></tr>'''
            elif messages[i]['role'] == 'assistant':
                messagelist += '''<tr style="background-color: #393939; display: inline-block;">
                <td>
                    <div class="agent">AI</div>
                  </td>
                  <td id="reply-''' + str(i) + '''">
                    <div class="message" messageid="''' + str(i) +'''" style="float: left;">'''
                lines = messages[i]['content'].split('\n')
                for j in lines:
                    messagelist += j + '<br>'

                messagelist += '''<br>
                    <div class="editbutton" style="float: right;">
                        <form hx-get="/edit" hx-target="#reply-''' + str(i) + '''" hx-swap="outerHTML">
                            <input type="hidden" name="messageid" value="''' + str(i) + '''">
                            <button class="btn">Edit</button>
                        </form>
                        <form hx-post="/delete" hx-target="closest tr" hx-swap="outerHTML">
                            <input type="hidden" name="messageid" value="''' + str(i) + '''">
                            <button class="btn">Delete</button>
                        </form>
                    </div>
                  </td></tr>'''
        messagelist += '<tr id="chattext" hx-get="/scroll" hx-trigger="load" hx-target="this" hx-swap="none, show:bottom"></tr></table>'
    return render_template_string(messagelist)


if __name__ == '__main__':
    app.run(port=8080)