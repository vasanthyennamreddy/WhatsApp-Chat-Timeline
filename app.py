from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.utils import secure_filename
import os

from datetime import datetime
from dateutil.relativedelta import relativedelta

app = Flask(__name__)
app.secret_key = os.urandom(27)

# HTML Content
pre = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="X-UA-Compatible" content="ie=edge">
  <title>WhatsApp Chat Timeline Plot</title>
</head>
<style>
div.google-visualization-tooltip {
  border: 1px solid #E0E0E0;
  font-family: Arial, Helvetica;
  padding: 6px 6px 6px 6px;
}
</style>
<body>
    
  <ul>
    <li>View site on Desktop, hover doesn't work on touch devices. Also site not optimized for small screens</li>
    <li>Scroll on the plot to view all the dates in order</li>
    <li>Hover on specific timeline to view the continous time (messages with in 5 minutes of each is considered continuous) for which chat continued</li>
    <li>If a chat spans two different days (during mid night) then hover time is the whole continuous time i.e, inclusive of both days</li>
  </ul>

  <script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>

  <script type="text/javascript">
    google.charts.load("current", {packages:["timeline"]});
    google.charts.setOnLoadCallback(drawChart);
    function drawChart() {
  
      var container = document.getElementById('chat-timeline');
      var chart = new google.visualization.Timeline(container);
      var dataTable = new google.visualization.DataTable();
      dataTable.addColumn({ type: 'string', id: 'Name' });
      dataTable.addColumn({ type: 'string', id: 'dummy bar label' });
      dataTable.addColumn({ type: 'string', role: 'tooltip' });
      dataTable.addColumn({ type: 'date', id: 'Start' });
      dataTable.addColumn({ type: 'date', id: 'Finish' });
      dataTable.addRows([
"""

post = """
      ]);
  
      var options = {
        timeline: { colorByRowLabel: true }
      };
  
      chart.draw(dataTable, options);
    }
  
  </script>
  
  <div id="chat-timeline" style="height: 720px"></div>

</body>
</html>
"""

ALLOWED_EXTENSIONS = {'txt'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_date(s_date):
    date_patterns = ['%d/%m/%y, %H:%M', '%d/%m/%Y, %H:%M', '%d/%m/%y, %I:%M %p', '%d/%m/%Y, %I:%M %p']

    for pattern in date_patterns:
        try:
            return datetime.strptime(s_date, pattern)
        except:
            pass

attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
human_readable = lambda delta: ['%d %s' % (getattr(delta, attr), getattr(delta, attr) > 1 and attr or attr[:-1]) for attr in attrs if getattr(delta, attr)]

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    in_file = request.files['file']
    if in_file.filename == '':
        flash('No file selected')
        return redirect(url_for('index'))
    if not allowed_file(in_file.filename):
        flash('Extension not .txt, are you using exported chat file ? Only .txt files are allowed')
        return redirect(url_for('index'))
    df = []
    filePath =  '/tmp/'
    filePath += secure_filename(in_file.filename)
    # Save file to read line by line (required for large files)
    in_file.save(os.path.join(filePath))
    with open(filePath, 'r') as fp:
        line = fp.readline()
        prev = None
        start = None
        prev_end = None
        while line:
            str_time = line.split('-')[0].strip()
            if prev:
                try:
                    curr = get_date(str_time)
                    # Ignore message if in 5 minutes of last message
                    if (curr - prev).total_seconds() <= 301:
                        prev = curr
                        last_line = line
                        line = fp.readline()
                        continue

                    prev_end = prev
                    if start:
                        time_slot = ' '.join(human_readable(relativedelta(prev_end, start)))
                        if time_slot == '':
                            time_slot = '< 1 minute'
                        df.append(
                            dict(Start=start, Finish=prev_end, Time=time_slot)
                        )
                    else:
                        time_slot = ' '.join(human_readable(relativedelta(prev_end, first_start)))
                        if time_slot == '':
                            time_slot = '< 1 minute'
                        df.append(
                            dict(Start=first_start, Finish=prev_end, Time=time_slot)
                        )

                    start = curr
                    prev = curr
                except:
                    # Handle long messages
                    pass
            else:
                try:
                    prev = get_date(str_time)
                    first_start = prev
                except:
                    # Handle long messages
                    pass

            last_line = line
            line = fp.readline()
        time_slot = ' '.join(human_readable(relativedelta(prev, start)))
        if time_slot == '':
            time_slot = '< 1 minute'
        df.append(
            dict(Start=start, Finish=prev, Time=time_slot)
        )
    # Delete Saved file
    os.remove(filePath)

    content = ""

    for slot in df:
        # Ignoring chats longing continuously more than a day! Cause considering only human chats
        try:
            if slot['Start'].day == slot['Finish'].day :
                content += f"""
                    [ '{slot['Start'].year}-{slot['Start'].month}-{slot['Start'].day}', '', '{slot['Time']}', new Date(0, 0, 0, {slot['Start'].hour}, {slot['Start'].minute}, 0), new Date(0, 0, 0, {slot['Finish'].hour}, {slot['Finish'].minute}, 0) ],"""
            else :
                content += f"""
                    [ '{slot['Start'].year}-{slot['Start'].month}-{slot['Start'].day}', '', '{slot['Time']}', new Date(0, 0, 0, {slot['Start'].hour}, {slot['Start'].minute}, 0), new Date(0, 0, 0, 24, 0, 0) ],"""
                content += f"""
                    [ '{slot['Finish'].year}-{slot['Finish'].month}-{slot['Finish'].day}', '', '{slot['Time']}', new Date(0, 0, 0, 0, 0, 0), new Date(0, 0, 0, {slot['Finish'].hour}, {slot['Finish'].minute}, 0) ],"""
        except:
            pass

    return pre + content + post

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
