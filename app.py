import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd
import SvApi
import math
import urllib
import json
import numpy as np
import requests

app = dash.Dash()

#Allow components generated in callbacks to be used in future callbacks (for Tabs)
app.config['suppress_callback_exceptions'] = True

external_css = ["http://mhco.dd:8443/default.css"]
#external_css = ["https://rawgit.com/benlevine13/DashStylesheets/master/default.css"]


for css in external_css:
    app.css.append_css({"external_url": css})

designObjs = SvApi.GetAll()
designs = []
for i in range (0, len(designObjs)):
    if designObjs[i]['Name'] not in designs and 'iFrame' not in designObjs[i]['Name']:
        designs.append(designObjs[i]['Name'])

def get_db(value):
    return  20 * math.log10(value)

def generate_table(dataframe, max_rows=10):
    return html.Table(
        # Header
        [html.Tr([html.Th(col) for col in dataframe.columns])] +

        # Body
        [html.Tr([
            html.Td(dataframe.iloc[i][col]) for col in dataframe.columns
        ]) for i in range(min(len(dataframe), max_rows))]
    )

schematics = {}
schematics['Sallen-Key Lowpass'] = 'https://systemvision.com/node/232411'
schematics['Boctor Notch Lowpass'] = 'https://systemvision.com/node/232406'
schematics['Multiple Feedback Lowpass'] = 'https://systemvision.com/node/232416'

app.layout = html.Div(
    [
        html.Div(
            [
            html.H1(
                'Lowpass Filter Design Wizard',
                className='eight columns',
            ),
            ],
            className='row wizard-title',
            # style = {'margin-bottom': '5px'}
        ),
        html.Div(
            [
            html.P('Step 1. Choose a base topology:'),
            dcc.Dropdown(
                id = 'design-selector',
                options = [{'label': i, 'value': i} for i in designs],
                value = 'Sallen-Key Lowpass'
                ),
            ],
            className='row topology',
            # style={'margin-bottom': '5px',
            #        'margin-top': '15px'}

        ),
        html.Div(
            [
                html.Div(
                    [
                        html.P('Step 2. Specify desired filter characteristics using the sliders below:'),
                        dcc.Slider(
                            id='gain-slider',
                            min=1.000001,
                            max=1000,
                            value=100,
                            step=0.1,
                            included=False
                        ),
                        html.Div(id='gain-output-container'),
                        dcc.Slider(
                            id='freq-slider',
                            marks={i: '{}'.format(10 ** i) for i in range(6)},
                            max=5,
                            value=2,
                            step=0.1,
                            included=False
                        ),
                        html.Div(id='freq-output-container', style={'margin-top': 20})
                    ],
                    className='five columns filters',
                    # style={'margin-left': '10px',
                    #        'margin-bottom': '5px',
                    #        'margin-top': '5px'}
                ),
                html.Div(
                    [
                        html.P('Step 3. Choose your mechanism for determining parameter values (If design equations are blank, re-choose design from dropdown above):'),
                        dcc.RadioItems(
                            id='param-type-selector',
                            options=[
                                {'label': 'Machine Learning Model', 'value': 'ML'},
                                {'label': 'Textbook Design Equations', 'value': 'equations'}
                            ],
                            value='ML',
                            labelStyle={'display': ''}
                        ),
                        html.Div(id='param-type-output',
                                  style={'margin-bottom': '10px', 'margin-right': '10px'}),
                    ],
                    className='five columns param-values',
                    style = {'margin-bottom': '5px',
                              'margin-top': '5px',
                              'float': 'right',
                              'margin-right': '10px'}
                ),
            ],
            className='row filters-param-values'
        ),

        html.Div(
            [
                html.Button('Launch Simulation', id='sim-button', style={'display': 'block','margin-left': 'auto', 'margin-right': 'auto'}),
                #html.Div(id='measure-display', style={'display':'block','margin-left': 'auto', 'margin-right': 'auto', 'text-align': 'center'}, children='Launch a simulation to generate results!',),

                # Hidden Div for Data Storage
                html.Div(id='bode-value', style = {'display': 'none'})
            ],
            style={'background-color': 'white',
                   'border-radius': '5px',
                   #'border': 'thin solid rgb(240, 240, 240)',
                   'margin-bottom': '10px',
                   'margin-left': '50%',
                   'transform': 'translateX(-50%)',
                   'margin-right': 'auto',
                   'display': 'inline-block'}
        ),

        html.Div(
            [
                html.Div(
                    [
                        html.Iframe(
                            id = 'schematic-viewer',
                            src = 'https://systemvision.com/node/219901',
                            #height='450',
                            width = '100%'
                        )
                    ],
                    className='eight columns',
                    # style={'margin-top': '20'}
                ),
                html.Div(
                    [
                        dcc.Graph(id = 'bode-gain')
                    ],
                    className='four columns',
                    # style={'margin-top': '20',
                    #        'border': 'thin solid rgb(240, 240, 240)'}
                )
            ],
            className='row app'
        ),

        html.Div(
            [
                html.Div(
                    children='Run a simulation to also search for relevant parts.',
                    id='part-search',
                    className='four columns',
                    # style={'margin-bottom': '10px'}
                ),
                html.Div(
                    [
                        html.P('Comprehensive advanced metrics')
                    ],
                    className='four columns',
                    # style={'margin-bottom': '10px'}
                ),
                html.Div(
                    [
                        dcc.Graph(id = 'bode-phase')
                    ],
                    className='four columns',
                    # style={'margin-bottom': '10px',
                    #        'border': 'thin solid rgb(240, 240, 240)'}
                )
            ],
            className='row'
        )
    ],
    className='ten columns offset-by-one',
    style={'background-color': 'white',
           'border-radius': '5px',
           # 'box-shadow': 'rgb(240, 240, 240) 5px 5px 5px 0px',
           'border': 'thin solid rgb(240, 240, 240)',
           'margin-bottom': '100px'}
)

@app.callback(
    dash.dependencies.Output('schematic-viewer', 'src'),
    [dash.dependencies.Input('design-selector', 'value')]
)
def update_viewer(input_value):
    return schematics[input_value]

@app.callback(
    dash.dependencies.Output('gain-output-container', 'children'),
    [dash.dependencies.Input('gain-slider', 'value')])
def display_gain(value):
    return 'Voltage Ratio: {0} | \
           dB Gain: {1:0.2f}'.format(value, get_db(value))

@app.callback(
    dash.dependencies.Output('freq-output-container', 'children'),
    [dash.dependencies.Input('freq-slider', 'value')])
def display_freq(value):
    return 'Cutoff Frequency: {0:0.2f} Hz'.format(10 ** value)

@app.callback(
    dash.dependencies.Output('measure-display', 'children'),
    [dash.dependencies.Input('bode-value', 'children')]
)
def print_measures(input):
    dff = pd.read_json(input[0], orient='split')
    DCGain = dff['YData'][0]
    for i in range(0, len(dff['YData'])):
       if dff['YData'][i] + 3 < DCGain:
           Cutoff = dff['XData'][i]
           break
    return 'Simulation results for this design:  Gain = {0} dB, Cutoff Frequency = {1} Hz'.format(DCGain, Cutoff)

@app.callback(
    dash.dependencies.Output('bode-gain', 'figure'),
    [dash.dependencies.Input('bode-value', 'children')]
)
def update_graph(input):
    print('updating gain')
    dff = pd.read_json(input[0], orient='split')
    data = [ go.Scatter(
        x = dff['XData'],
        y = dff['YData'],
        line = dict(
            color = 'rgb(0,110,190)',
            width=4
        ),
        marker = dict(
            color = 'rgb(150,200,255)',
            size=15
        )
    )]
    layout = go.Layout(
        title= 'Gain',
        titlefont = dict (
            family = 'AV Roman',
            size=14
        ),
        xaxis= dict(
            type = 'log',
            autorange=True,
            title = 'Frequency (Hz)',
            zerolinewidth = 3,
            gridwidth = 1,
            zerolinecolor = 'rgb(61, 67, 75)',
            gridcolor = 'rgb(221,221,221)'
        ),
        yaxis = dict(
            autorange=True,
            title = 'Gain (dB)',
            zerolinewidth=3,
            gridwidth=1,
            zerolinecolor='rgb(61, 67, 75)',
            gridcolor='rgb(221,221,221)'
        ),
        images = dict (
            opacity = 1,
            xref = 'paper',
            yref = 'paper',
            sizex = 0.2,
            sizey = 0.2,
            source = "data:image/png;base64,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",
            y = 1.1,
            x = 0
        ),
        font = dict(
            size=18,
            family = 'Carter Regular'
        ))


    fig = go.Figure(data=data, layout=layout)
    return fig

@app.callback(
    dash.dependencies.Output('bode-phase', 'figure'),
    [dash.dependencies.Input('bode-value', 'children')]
)
def update_graph(input):
    print('updating phase')
    dff = pd.read_json(input[1], orient='split')
    data = [ go.Scatter(
        x = dff['XData'],
        y = dff['YData'],
        line = dict(
            color='rgb(0,110,190)',
            width=4
        )
    )]
    layout = go.Layout(
        title = 'Phase',
        titlefont = dict(
            family='AV Roman',
            size=18
        ),
        xaxis= dict(
            type = 'log',
            autorange=True,
            title = 'Frequency (Hz)'
        ),
        yaxis = dict(
            autorange=True,
            title = 'Phase',
            zerolinewidth=3,
            gridwidth=1,
            zerolinecolor='rgb(61, 67, 75)',
            gridcolor='rgb(221,221,221)'
        ),
        font = dict(
            size = 14,
            family = 'Carter Regular'
        )
)
    fig = go.Figure(data=data, layout=layout)
    return fig

@app.callback(
    dash.dependencies.Output('param-type-output', 'children'),
    [dash.dependencies.Input('param-type-selector','value')]
)
def display_choices(value):
    if value == 'ML':
        return [
            html.Button('Predict Parameter', id='param-button'),
            html.Div(id='ml-data', style={'display': 'none'}),
            html.P(id='ml-prediction', children='Click button to generate prediction', style={'float': 'right'})
        ]
    elif value == 'equations':
        return [html.Div(id = 'equation-objs')]
    return 'Not sure how we ended up here.'

@app.callback(
    dash.dependencies.Output('ml-data', 'children'),
    [dash.dependencies.Input('param-button', 'n_clicks')],
    [dash.dependencies.State('gain-slider', 'value'),
     dash.dependencies.State('freq-slider', 'value')]
)
def guess_resistance(n_clicks, input1, input2):
    # Do a bunch of ML API
    data = {

        "Inputs": {

            "input1":
                {
                    "ColumnNames": ["DC_Gain", "CutoffFrequency"],
                    "Values": [[input1, input1], [10 ** input2, 10 ** input2], ]
                }, },
        "GlobalParameters": {
        }
    }

    body = str.encode(json.dumps(data))

    url = 'https://ussouthcentral.services.azureml.net/workspaces/0977ffcf86024f65a37b3eaddad8a420/services/b38910b37f00402eb21c752874a9bac5/execute?api-version=2.0&details=true'
    api_key = 'oi0zEG4TQhU1nZeKLnFBpd95Lgzf/sN6AtZy6nFPboyWKs6VRFimka5Ck+tOsyf+LHTlSJTK88h0JPShxRX/sg=='  # Replace this with the API key for the web service
    headers = {'Content-Type': 'application/json', 'Authorization': ('Bearer ' + api_key)}

    req = urllib.request.Request(url, body, headers)
    response = urllib.request.urlopen(req)

    result = response.read()
    answer = json.loads(result)

    predicted_value = float(answer['Results']['output1']['value']['Values'][0][0])
    return predicted_value

@app.callback(
    dash.dependencies.Output('ml-prediction', 'children'),
    [dash.dependencies.Input('ml-data', 'children')],
    [dash.dependencies.State('gain-slider', 'value'),
     dash.dependencies.State('freq-slider', 'value')]
)
def display_prediction(value, input1, input2):
    return 'Set R1 to {0:.4f} for DC Gain of {1:.2f} dB and Cutoff Freq of {2:.2f} Hz'.format(value, get_db(input1),
                                                                                              10 ** input2)


@app.callback(
    dash.dependencies.Output('equation-objs', 'children'),
    [dash.dependencies.Input('design-selector', 'value')],
    [dash.dependencies.State('gain-slider', 'value'),
     dash.dependencies.State('freq-slider', 'value')]
)
def show_equations(design, gain, freq):
    if design == 'Sallen-Key Lowpass':
        return [
                html.P(children='Choose values for c1 and r3 (reference schematic + design equations)',id='sallen-explain'),
                dcc.Slider(
                        id = 'sallen-c1-slider',
                        min = 1,
                        max = 50,
                        step = 0.1,
                        marks = {
                            1: '1 nF',
                            10: '10 nF',
                            20: '20nF',
                            30: '30nF',
                            40: '40 nF',
                            50: '50 nF'
                        },
                        included = False),
                html.Div(
                    id = 'sallen-r3-container',
                    children=[
                        dcc.Slider(
                            id = 'sallen-r3-slider',
                            min = 100,
                            max = 10000,
                            marks={
                                100: '100 Ohms',
                                1000: '1000 Ohms',
                                10000: '10000 Ohms'
                            },
                            step = 1,
                            included = False
                        )],
                    style = {'margin-top': 20, 'margin-bottom': 20}
                ),

                #Hidden div to store all necessary parameters
                html.Div(id = 'sallen-values', style = {'display': 'none'}),
                html.Div(id = 'sallen-display')
            ]
    elif design == 'Boctor Notch Lowpass':
        return [
                html.P(children='Choose values for r6, r5, and c1 (reference schematic + design equations)',id='boctor-explain'),
                dcc.Slider(
                    id='boctor-r6-slider',
                    min=100,
                    max=10000,
                    marks={
                        100: '100 Ohms',
                        1000: '1000 Ohms',
                        10000: '10000 Ohms'
                    },
                    step=1,
                    included=False
                ),
                html.Div(
                    id = 'boctor-r5-container',
                    children=[
                        dcc.Slider(
                    id='boctor-r5-slider',
                    min=100,
                    max=10000,
                    marks={
                        100: '100 Ohms',
                        1000: '1000 Ohms',
                        10000: '10000 Ohms'
                    },
                    step=1,
                    included=False
                )],
                    style = {'margin-top': 20}
                ),
                html.Div(
                    id = 'boctor-c1-container',
                    children=[
                        dcc.Slider(
                    id='boctor-c1-slider',
                    min=1,
                    max=50,
                    step=0.1,
                    marks={
                        1: '1 nF',
                        10: '10 nF',
                        20: '20nF',
                        30: '30nF',
                        40: '40 nF',
                        50: '50 nF'
                    },
                    included=False
                )],
                    style = {'margin-top': 20, 'margin-bottom': 20}
                ),
                #Hidden div to store all necessary parameters
                html.Div(id='boctor-values', style={'display': 'none'}),
                html.Div(id='boctor-display')
            ]
    elif design == 'Multiple Feedback Lowpass':
        return [
                html.P(children='Choose value for c5 (reference schematic + design equations)',id='feedback-explain'),
                html.Div(
                    id = 'feedback-c5-container',
                    children=[
                        dcc.Slider(
                    id='feedback-c5-slider',
                    min=1,
                    max=50,
                    step=0.1,
                    marks={
                        1: '1 nF',
                        10: '10 nF',
                        20: '20nF',
                        30: '30nF',
                        40: '40 nF',
                        50: '50 nF'
                    },
                    included=False
                )],
                    style = {'margin-top': 20, 'margin-bottom': 20}
                ),
                #Hidden div to store all necessary parameters
                html.Div(id='feedback-values', style={'display': 'none'}),
                html.Div(id='feedback-display')
            ]
    return 'Try to do math to make a {} filter with {} dB gain and {} Hz cutoff frequency'.format(design, gain, 10 ** freq)

#Sallen equations

@app.callback(
    dash.dependencies.Output('sallen-values', 'children'),
    [dash.dependencies.Input('sallen-c1-slider', 'value'),
     dash.dependencies.Input('sallen-r3-slider', 'value'),
     dash.dependencies.Input('gain-slider', 'value'),
     dash.dependencies.Input('freq-slider', 'value')]
)
def calculate_sallen(c1, r3, gain, freq):
    sallenParams = np.empty((6,3), dtype=object)

    c1 = c1 * (10 ** -9)
    freq = 10 ** freq
    k = c1 * (2 * math.pi * freq)
    m = 0.25 + (gain-1)
    c2 = m * c1
    r1 = 2 / k
    r2 = 1 / (2 * m * k)
    r4 = r3 / (gain-1)


    sallenParams[0][0] = 'c1'
    sallenParams[0][1] = 'capacitance_value'
    sallenParams[0][2] = c1

    sallenParams[1][0] = 'r3'
    sallenParams[1][1] = 'resistance_value'
    sallenParams[1][2] = r3

    sallenParams[2][0] = 'c2'
    sallenParams[2][1] = 'capacitance_value'
    sallenParams[2][2] = c2

    sallenParams[3][0] = 'r1'
    sallenParams[3][1] = 'resistance_value'
    sallenParams[3][2] = r1

    sallenParams[4][0] = 'r2'
    sallenParams[4][1] = 'resistance_value'
    sallenParams[4][2] = r2

    sallenParams[5][0] = 'r4'
    sallenParams[5][1] = 'resistance_value'
    sallenParams[5][2] = r4

    sallenReturn = pd.DataFrame(sallenParams).to_json(orient='split')

    print('updated parameter inputs for Sallen-Key')
    return sallenReturn

#Sallen display
@app.callback(
    dash.dependencies.Output('sallen-display', 'children'),
    [dash.dependencies.Input('sallen-values', 'children')]
)
def display_sallen(input):
    displayParams = pd.read_json(input, orient='split')



#Boctor equations
@app.callback(
    dash.dependencies.Output('boctor-values', 'children'),
    [dash.dependencies.Input('boctor-r6-slider', 'value'),
     dash.dependencies.Input('boctor-r5-slider', 'value'),
     dash.dependencies.Input('boctor-c1-slider', 'value'),
     dash.dependencies.Input('gain-slider', 'value'),
     dash.dependencies.Input('freq-slider', 'value')]
)
def calculate_boctor(r6, r5, c1, gain, freq):
    boctorParams = np.empty((8,3), dtype=object)

    #MATH
    c1 = c1 * (10 ** -9)
    freq = 10 ** freq
    r4 = 1 / ((2 * math.pi * freq) * c1 * 2)
    r2 = 1 / ((1 / r4) + (1/ r6))
    r1 = 0.5 * (100*(r6/r4)-1)
    c2 = 4 * r4 * c1 /r6
    r3 = r5 * ((r6/r1) + (2*(c1/c2)))

    boctorParams[0][0] = 'r6'
    boctorParams[0][1] = 'resistance_value'
    boctorParams[0][2] = r6

    boctorParams[1][0] = 'r5'
    boctorParams[1][1] = 'resistance_value'
    boctorParams[1][2] = r5

    boctorParams[2][0] = 'c1'
    boctorParams[2][1] = 'capacitance_value'
    boctorParams[2][2] = c1

    boctorParams[3][0] = 'r4'
    boctorParams[3][1] = 'resistance_value'
    boctorParams[3][2] = r4

    boctorParams[4][0] = 'r2'
    boctorParams[4][1] = 'resistance_value'
    boctorParams[4][2] = r2

    boctorParams[5][0] = 'r1'
    boctorParams[5][1] = 'resistance_value'
    boctorParams[5][2] = r1

    boctorParams[6][0] = 'r3'
    boctorParams[6][1] = 'resistance_value'
    boctorParams[6][2] = r3

    boctorParams[7][0] = 'c2'
    boctorParams[7][1] = 'capacitance_value'
    boctorParams[7][2] = c2

    boctorReturn = pd.DataFrame(boctorParams).to_json(orient='split')

    print('updated parameter inputs for Boctor Notch')
    return boctorReturn


#Feedback equations
@app.callback(
    dash.dependencies.Output('feedback-values', 'children'),
    [dash.dependencies.Input('feedback-c5-slider', 'value'),
     dash.dependencies.Input('gain-slider', 'value'),
     dash.dependencies.Input('freq-slider', 'value')]
)
def calculate_feedback(c2, gain, freq):
    feedbackParams = np.empty((5,3), dtype=object)

    #MATH
    c2 = c2 * (10 ** -9)
    freq = 10 ** freq
    k = (2 * math.pi * freq) * c2
    c1 = 4 * (gain + 1) * c2
    r1 = 1 / (2 * gain * k)
    r3 = 1 / (2 * (gain + 1) * k)
    r2 = 1 / (2 * k)

    feedbackParams[0][0] = 'c2'
    feedbackParams[0][1] = 'capacitance_value'
    feedbackParams[0][2] = c2

    feedbackParams[1][0] = 'c1'
    feedbackParams[1][1] = 'capacitance_value'
    feedbackParams[1][2] = c1

    feedbackParams[2][0] = 'r1'
    feedbackParams[2][1] = 'resistance_value'
    feedbackParams[2][2] = r1

    feedbackParams[3][0] = 'r3'
    feedbackParams[3][1] = 'resistance_value'
    feedbackParams[3][2] = r3

    feedbackParams[4][0] = 'r2'
    feedbackParams[4][1] = 'resistance_value'
    feedbackParams[4][2] = r2

    feedbackReturn = pd.DataFrame(feedbackParams).to_json(orient='split')

    print('updated parameter inputs for Multiple Feedback')
    return feedbackReturn

@app.callback(
    dash.dependencies.Output('bode-value', 'children'),
    [dash.dependencies.Input('sim-button', 'n_clicks')],
    [dash.dependencies.State('design-selector', 'value'),
     dash.dependencies.State('param-type-output', 'children'),
     dash.dependencies.State('param-type-selector', 'value')]
)
def on_click(n_clicks, design, input, select):
    if n_clicks > 0:
        if select == 'ML':
            designID, revisionID = SvApi.FindDesign(designObjs, design)
            simDesign = SvApi.GetDesign(designID, revisionID)
            simDesign = SvApi.CreateRevision(simDesign)
            simDesign = simDesign.json()

            #search for div holding r1
            search = 0
            while input[search]['props']['id'] != 'ml-data':
                search += 1
            r1 = input[search]['props']['children']


            simDesign = SvApi.ChangeProperty(simDesign, 'r1', 'resistance_value', r1)
            response = SvApi.PutDesign(simDesign)

            if design == 'Sallen-Key Lowpass':
                dfGain, dfPhase = SvApi.RunSallenKey()
                jsonGain = dfGain.to_json(orient='split')
                jsonPhase = dfPhase.to_json(orient='split')
            elif design == 'Boctor Notch Lowpass':
                dfGain, dfPhase = SvApi.RunBoctorNotch()
                jsonGain = dfGain.to_json(orient='split')
                jsonPhase = dfPhase.to_json(orient='split')
            elif design == 'Multiple Feedback Lowpass':
                dfGain, dfPhase = SvApi.RunMultipleFeedback()
                jsonGain = dfGain.to_json(orient='split')
                jsonPhase = dfPhase.to_json(orient='split')

        if select == 'equations':
            if design == 'Sallen-Key Lowpass':
                search = 0
                while (input[0]['props']['children'][search]['props']['id'] != 'sallen-values'):
                    search += 1
                paramInputs = (input[0]['props']['children'][search]['props']['children'])
                paramInputs = pd.read_json(paramInputs, orient='split')
                paramInputs = paramInputs.values
                designID, revisionID = SvApi.FindDesign(designObjs, design)
                simDesign = SvApi.GetDesign(designID, revisionID)
                print (simDesign.json())
                simDesign = SvApi.CreateRevision(simDesign)
                simDesign = simDesign.json()
                for i in range (0,len(paramInputs)):
                        simDesign = SvApi.ChangeProperty(simDesign, paramInputs[i][0], paramInputs[i][1], paramInputs[i][2])
                        response = SvApi.PutDesign(simDesign)
                dfGain, dfPhase = SvApi.RunSallenKey()
                jsonGain = dfGain.to_json(orient='split')
                jsonPhase = dfPhase.to_json(orient='split')
            if design == 'Boctor Notch Lowpass':
                search = 0
                while (input[0]['props']['children'][search]['props']['id'] != 'boctor-values'):
                    search += 1
                paramInputs = (input[0]['props']['children'][search]['props']['children'])
                paramInputs = pd.read_json(paramInputs, orient='split')
                paramInputs = paramInputs.values
                designID, revisionID = SvApi.FindDesign(designObjs, design)
                simDesign = SvApi.GetDesign(designID, revisionID)
                simDesign = SvApi.CreateRevision(simDesign)
                simDesign = simDesign.json()
                for i in range (0,len(paramInputs)):
                    simDesign = SvApi.ChangeProperty(simDesign, paramInputs[i][0], paramInputs[i][1], paramInputs[i][2])
                    response = SvApi.PutDesign(simDesign)
                dfGain, dfPhase = SvApi.RunBoctorNotch()
                jsonGain = dfGain.to_json(orient='split')
                jsonPhase = dfPhase.to_json(orient='split')
            if design == 'Multiple Feedback Lowpass':
                search = 0
                while (input[0]['props']['children'][search]['props']['id'] != 'feedback-values'):
                    search += 1
                paramInputs = (input[0]['props']['children'][search]['props']['children'])
                paramInputs = pd.read_json(paramInputs, orient='split')
                paramInputs = paramInputs.values
                designID, revisionID = SvApi.FindDesign(designObjs, design)
                simDesign = SvApi.GetDesign(designID, revisionID)
                simDesign = SvApi.CreateRevision(simDesign)
                simDesign = simDesign.json()
                for i in range (0,len(paramInputs)):
                    simDesign = SvApi.ChangeProperty(simDesign, paramInputs[i][0], paramInputs[i][1], paramInputs[i][2])
                    response = SvApi.PutDesign(simDesign)
                dfGain, dfPhase = SvApi.RunMultipleFeedback()
                jsonGain = dfGain.to_json(orient='split')
                jsonPhase = dfPhase.to_json(orient='split')
        return jsonGain, jsonPhase

@app.callback(
    dash.dependencies.Output('part-search', 'children'),
    [dash.dependencies.Input('bode-value', 'children')],
    [dash.dependencies.State('param-type-output', 'children'),
     dash.dependencies.State('param-type-selector', 'value'),
     dash.dependencies.State('design-selector', 'value')]
)
def search_parts(flag, input, select, design):
    if select == 'ML':
        # search for div holding r1
        search = 0
        while input[search]['props']['id'] != 'ml-data':
            search += 1
        r1 = input[search]['props']['children']
        rounded = round(r1, 0)
        query = "%i ohm resistor" % (rounded)
        args = [
            ('q', query),
            ('start', 0),
            ('limit', 5)
        ]

        octoUrl = "http://octopart.com/api/v3/parts/search"
        octoUrl += "?apikey=14dff834"
        octoUrl += '&' + urllib.parse.urlencode(args)

        octoData = urllib.request.urlopen(octoUrl).read()

        search_response = json.loads(octoData)
        nameArray = []
        partNoArray = []
        priceArray = []
        for result in search_response['results']:
            part = result['item']
            nameArray.append(part['brand']['name'])
            partNoArray.append(part['mpn'])
            priceArray.append(part['offers'][0]['prices']['USD'][0][1])

        df = {'Supplier': nameArray, 'Part No.': partNoArray, 'Price': priceArray}
        df = pd.DataFrame(data=df)
        display_table = generate_table(df)
        return [display_table]

    if select == 'equations':
        if design == 'Sallen-Key Lowpass':
            search = 0
            while (input[0]['props']['children'][search]['props']['id'] != 'sallen-values'):
                search += 1
            paramInputs = (input[0]['props']['children'][search]['props']['children'])
            paramInputs = pd.read_json(paramInputs, orient='split')
            paramInputs = paramInputs.values

            r1 = paramInputs[1][2]
            rounded = round(r1, 0)
            query = "%i ohm resistor" % (rounded)
            args = [
                ('q', query),
                ('start', 0),
                ('limit', 5)
            ]

            octoUrl = "http://octopart.com/api/v3/parts/search"
            octoUrl += "?apikey=14dff834"
            octoUrl += '&' + urllib.parse.urlencode(args)

            octoData = urllib.request.urlopen(octoUrl).read()

            search_response = json.loads(octoData)


            nameArray = []
            partNoArray = []
            priceArray = []

            for result in search_response['results']:
                part = result['item']
                nameArray.append(part['brand']['name'])
                partNoArray.append(part['mpn'])
                priceArray.append(part['offers'][0]['prices']['USD'][0][1])


            df = {'Supplier': nameArray, 'Part No.': partNoArray, 'Price': priceArray}
            df = pd.DataFrame(data=df)
            display_table = generate_table(df)
            return [display_table]

        if design == 'Boctor Notch Lowpass':
            search = 0
            while (input[0]['props']['children'][search]['props']['id'] != 'boctor-values'):
                search += 1
            paramInputs = (input[0]['props']['children'][search]['props']['children'])
            paramInputs = pd.read_json(paramInputs, orient='split')
            paramInputs = paramInputs.values

            r1 = paramInputs[0][2]
            rounded = round(r1, 0)
            query = "%i ohm resistor" % (rounded)
            args = [
                ('q', query),
                ('start', 0),
                ('limit', 5)
            ]

            octoUrl = "http://octopart.com/api/v3/parts/search"
            octoUrl += "?apikey=14dff834"
            octoUrl += '&' + urllib.parse.urlencode(args)
            octoData = urllib.request.urlopen(octoUrl).read()
            search_response = json.loads(octoData)

            nameArray = []
            partNoArray = []
            priceArray = []

            for result in search_response['results']:
                part = result['item']
                nameArray.append(part['brand']['name'])
                partNoArray.append(part['mpn'])
                priceArray.append(part['offers'][0]['prices']['USD'][0][1])

            df = {'Supplier': nameArray, 'Part No.': partNoArray, 'Price': priceArray}
            df = pd.DataFrame(data=df)
            display_table = generate_table(df)
            return [display_table]


        if design == 'Multiple Feedback Lowpass':
            search = 0
            while (input[0]['props']['children'][search]['props']['id'] != 'feedback-values'):
                search += 1
            paramInputs = (input[0]['props']['children'][search]['props']['children'])
            paramInputs = pd.read_json(paramInputs, orient='split')
            paramInputs = paramInputs.values

            r1 = paramInputs[2][2]
            rounded = round(r1, 0)
            query = "%i ohm resistor" % (rounded)
            args = [
                ('q', query),
                ('start', 0),
                ('limit', 5)
            ]

            octoUrl = "http://octopart.com/api/v3/parts/search"
            octoUrl += "?apikey=14dff834"
            octoUrl += '&' + urllib.parse.urlencode(args)
            octoData = urllib.request.urlopen(octoUrl).read()
            search_response = json.loads(octoData)

            nameArray = []
            partNoArray = []
            priceArray = []

            for result in search_response['results']:
                part = result['item']
                nameArray.append(part['brand']['name'])
                partNoArray.append(part['mpn'])
                priceArray.append(part['offers'][0]['prices']['USD'][0][1])

            df = {'Supplier': nameArray, 'Part No.': partNoArray, 'Price': priceArray}
            df = pd.DataFrame(data=df)
            display_table = generate_table(df)
            return [display_table]



if __name__ == '__main__':
    app.run_server()