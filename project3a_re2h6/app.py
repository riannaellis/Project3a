from flask import Flask, render_template, request, url_for, flash, redirect, abort
import csv
from datetime import datetime
import requests
import pygal

# make a Flask application object called app
app = Flask(__name__)
app.config["DEBUG"] = True
app.config['SECRET_KEY'] = 'your secret key'
API_KEY = 'WFZIS351NY5T9JDF'

#use @app.route to create a flask view for the index page of the web app
@app.route('/')
def index():
    symbols_list = []

    with open("stocks.csv", mode='r') as file:
        csv_reader = csv.reader(file)

        next(csv_reader, None)

        for row in csv_reader:
            symbols_list.append(row[0])


    chart_list = ("Bar", "Line")
    time_series_list = ("Intraday", "Daily", "Weekly", "Monthly")

    #send the agents to the index.html
    return render_template("index.html", symbols_list=symbols_list, chart_list=chart_list, time_series_list=time_series_list)

@app.route("/results", methods=['POST'])
def results():
    symbol = request.form.get("symbol")
    chart_type = request.form.get("chart")
    time_series = request.form.get("timeSeries")
    start_date = request.form.get("startdate")
    end_date = request.form.get("enddate")

    #Make sure all fields have a value
    if not symbol or not chart_type or not time_series or not start_date or not end_date:
        flash("ERROR: Please fill out all fields before submitting.")
        return(redirect(url_for("index")))
    
    #Convert date objects
    start_date = datetime.strptime(request.form.get("startdate"), "%Y-%m-%d")
    end_date = datetime.strptime(request.form.get("enddate"), "%Y-%m-%d")

    #Make sure the end date is after the start date
    if not check_end_date(start_date, end_date):
        flash("ERROR: Please enter an end date that occurs after the start date.")
        return(redirect(url_for("index")))
    
    #Make sure the symbol is valid
    isvalid, value = check_symbol(symbol, API_KEY)

    #Flash an error if the symbol is invalid
    if isvalid == False:
        flash(value)
        return(redirect(url_for("index")))
    
    #Get time series data
    try:
        time_series_data = get_time_series(value, time_series)
    except:
        flash("There was an error retrieving the time series data. Please try again.")
        return(redirect(url_for("index")))
    
    try:
        chart_path = (fetch_and_plot_stock_data(symbol, start_date, end_date, chart_type, API_KEY, time_series_data, value)).replace("static/", "")
    except:
        flash("Please try again.")
        return(redirect(url_for("index")))

    return render_template("results.html", symbol = symbol, chart_type=chart_type, time_series=time_series, start_date=start_date, end_date=end_date, chart_path=chart_path)

def check_end_date(start_date, end_date):

    if (end_date < start_date):
        return False
    else:
        return True

def check_symbol(symbol, api_key):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&apikey={api_key}'
    message = ""

    try:
        response = requests.get(url)
        data = response.json()
        

        # Check if the API request was successful and the symbol is valid
        if 'Error Message' in data:
            message = "No data found for stock symbol. Please try again."
            return False, message
        elif 'Note' in data:
            message = "API limit reached. Please wait before trying again."
            return False, message
        elif 'Time Series (Daily)' not in data:
            message = "Unexpected error. Please try again."
            return False, message
        else:
            return True, data  # Return the data itself when successful
    
    except requests.exceptions.RequestException as e:
        return False, message == "Error fetching data."

def get_time_series(data, time_series):
    if time_series == "Intraday":
        time_series_data = data.get('Time Series (Intraday)', {})
        return time_series_data
    elif time_series == "Daily":
        time_series_data = data.get('Time Series (Daily)', {})
        return time_series_data
    elif time_series == "Weekly":
        time_series_data = data.get('Time Series (Weekly)', {})
        return time_series_data
    elif time_series == "Monthly":
        time_series_data = data.get('Time Series (Monthly)', {})
        return time_series_data

def fetch_and_plot_stock_data(symbol, start_date, end_date, chart_type, api_key, time_series_data, data):
    
    # Filter data by date range
    filtered_data = {date: values for date, values in time_series_data.items() 
                     if start_date <= datetime.strptime(date, '%Y-%m-%d') <= end_date}
    
    if not filtered_data:
        flash("No data available for the selected date range.")
        return(redirect(url_for("index")))
    
    # Prepare data for plotting
    dates = list(filtered_data.keys())
    open_prices = [float(data['1. open']) for data in filtered_data.values()]
    high_prices = [float(data['2. high']) for data in filtered_data.values()]
    low_prices = [float(data['3. low']) for data in filtered_data.values()]
    close_prices = [float(data['4. close']) for data in filtered_data.values()]
    
    # Create the chart using Pygal based on the selected chart type
    if chart_type.lower() == 'line':
        chart = pygal.Line(x_label_rotation=45) # Line chart
    elif chart_type.lower() == 'bar':
        chart = pygal.Bar(x_label_rotation=45) # Bar chart 
    else:
        flash("Error selecting chart type.")
        return(redirect(url_for("index")))

    # Set chart title and labels
    chart.title = f'{symbol} Stock Data from {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}'
    chart.x_labels = dates

    # Add each series to the chart (Open, High, Low, Close)
    chart.add('Open', open_prices)
    chart.add('High', high_prices)
    chart.add('Low', low_prices)
    chart.add('Close', close_prices)
    
    # Save image as svg file
    filepath = f'static/stock_data_charts/{symbol}_stock_data_chart.svg'
    chart.render_to_file(filepath)
    print(f"Chart saved at: {filepath}")
    
    #return filepath
    return filepath

app.run(host="0.0.0.0")