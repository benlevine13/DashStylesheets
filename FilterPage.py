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




app = dash.Dash()

#Allow components generated in callbacks to be used in future callbacks (for Tabs)
app.config['suppress_callback_exceptions'] = True

external_css = ["https://rawgit.com/benlevine13/DashStylesheets/master/default.css"]


for css in external_css:
    app.css.append_css({"external_url": css})

designObjs = SvApi.GetAll()
designs = []
for i in range (0, len(designObjs)):
    if designObjs[i]['Name'] not in designs and 'iFrame' not in designObjs[i]['Name']:
        designs.append(designObjs[i]['Name'])

def get_db(value):
    return  20 * math.log10(value)

schematics = {}
schematics['Sallen-Key Lowpass'] = 'https://systemvision.com/node/232411'
schematics['Boctor Notch Lowpass'] = 'https://systemvision.com/node/232406'
schematics['Multiple Feedback Lowpass'] = 'https://systemvision.com/node/232416'

app.layout = html.Div([
    html.H2('Lowpass Filter Design Wizard'),
    html.Div(style = {'width': '48%', 'display': 'inline-block'}, children = [
    html.Div(style = {}, children = [
        html.H6("Please choose a topology from the drowdown below:"),
        dcc.Dropdown(
            id = 'design-selector',
            options = [{'label': i, 'value': i} for i in designs],
            value = 'Sallen-Key Lowpass'
        ),
        html.Iframe(
            id = 'schematic-viewer',
            src = 'https://systemvision.com/node/219901',
            height = '720',
            width = '100%'
        )]),
    html.Div(id='equation-display', style = {'color': 'rgb(150,200,255'})

    ]),

    html.Div(style = {'display': 'inline-block', 'width': '48%','float': 'right'}, children = [

        html.Div(style = {'boxShadow': '0px 0px 5px 5px rgba(204,204,204,0.4)',
                          'marginBottom': '10px'}, children = [
            dcc.Slider(
                id = 'gain-slider',
                min = 1.000001,
                max = 1000,
                value = 100,
                step = 0.1,
                included = False
            ),
            html.Div(id = 'gain-output-container'),
            dcc.Slider(
                id = 'freq-slider',
                marks = {i: '{}'.format(10 ** i) for i in range(6)},
                max = 5,
                value = 2,
                step = 0.1,
                included = False
            ),
            html.Div(id = 'freq-output-container', style = {'margin-top': 20})
        ]),

        dcc.Tabs(
            id = 'tabs',
            style = {'fontWeight': 'bold'},
            tabs = [{'label': 'ML Model', 'value': 'ML'},
                    {'label': 'Design Equations', 'value': 'equations'}],
            value = 'equations'
        ),
        html.Div(id='tab-output', style = {'borderStyle': 'solid', 'borderWidth': '1px'}),
        html.Button('Launch Simulation', id='sim-button'),

        #Source voltage and load resistance
        #dcc.Input(),
        #dcc.Input(),

        # Hidden Div for Data Storage
        html.Div(id='bode-value', style = {'display': 'none'}),

        html.Div(id='measure-display'),
        dcc.Graph(id = 'bode-gain'),
        dcc.Graph(id = 'bode-phase')
    ])

], style = {'padding': '0px 10px 15px 10px',
            'marginLeft': 'auto', 'marginRight': 'auto'})

@app.callback(
    dash.dependencies.Output('schematic-viewer', 'src'),
    [dash.dependencies.Input('design-selector', 'value')]
)
def update_viewer(input_value):
    return schematics[input_value]

@app.callback(
    dash.dependencies.Output('equation-display', 'children'),
    [dash.dependencies.Input('design-selector', 'value')]
)
def update_equations(input_value):
    if input_value == 'Sallen-Key Lowpass':
        return dcc.Markdown('''
## Sallen-Key Lowpass Design Equations
These equations and more info can be found [HERE](http://www.analog.com/media/en/training-seminars/design-handbooks/Basic-Linear-Design/Chapter8.pdf)
### Choose C1, R3
### Then:
k = Freq * C1

m = (Gain-1) / 4

C2 = m * C1

R1 = 2 / k

R2 = 1 / (2 * m * k)

R4 = R3 / (Gain-1)
''')

    elif input_value == 'Boctor Notch Lowpass':
        return dcc.Markdown('''
## Boctor Notch Lowpass Design Equations
These equations and more info can be found [HERE](http://www.analog.com/media/en/training-seminars/design-handbooks/Basic-Linear-Design/Chapter8.pdf)
### Choose R6, R5, C1
### Then:
R4 = 1 / (2 * Freq * C1)

R2 = (R4 * R6) / (R4 = R6)

R1 = 1/2 * [(R6/R4)-1]

R3 = R5 * [(R6/R1) + 2*(C1/C2)]

C2 = (4 * R4 * C1) / R6
''')
    elif input_value == 'Multiple Feedback Lowpass':
        return dcc.Markdown('''
## Multiple Feedback Lowpass Design Equations
These equations and more info can be found [HERE](http://www.analog.com/media/en/training-seminars/design-handbooks/Basic-Linear-Design/Chapter8.pdf)
### Choose C5
### Then:
k = Freq * C5

C2 = 4 * (Gain+1) * C5

R1 = 1 / (2 * Gain * k)

R3 = 1 / [2 * (Gain + 1) * k]

R4 = 1 / (2 * k)
''')
    else:
        return 'No equations defined for selected design.'


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
        y = dff['YData']
    )]
    layout = go.Layout(
        xaxis= dict(
            type = 'log',
            autorange=True,
            title = 'Frequency (Hz)'
        ),
        yaxis = dict(
            autorange=True,
            title = 'Gain (dB)'
        )
    )
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
        y = dff['YData']
    )]
    layout = go.Layout(
        xaxis= dict(
            type = 'log',
            autorange=True,
            title = 'Frequency (Hz)'
        ),
        yaxis = dict(
            autorange=True,
            title = 'Phase'
        )
    )
    fig = go.Figure(data=data, layout=layout)
    return fig

@app.callback(
    dash.dependencies.Output('tab-output', 'children'),
    [dash.dependencies.Input('tabs','value')]
)
def display_choices(value):
    if value == 'ML':
        return html.Div(
            id = 'ML-objs',
            children = [
            html.Button('Predict Parameter', id='param-button'),
            html.Div(id='r1-data', style={'display': 'none'}),
            html.Div(id='r1-prediction', style={'textAlign': 'center', 'fontWeight': 'bold'})
        ])
    elif value == 'equations':
        return html.Div(
            id = 'equation-objs'
        )
    return 'Not sure how we ended up here.'

@app.callback(
    dash.dependencies.Output('equation-objs', 'children'),
    [dash.dependencies.Input('design-selector', 'value')],
    [dash.dependencies.State('gain-slider', 'value'),
     dash.dependencies.State('freq-slider', 'value')]
)
def show_equations(design, gain, freq):
    if design == 'Sallen-Key Lowpass':
        return html.Div(
            id='sallen-objs',
            children=[
                html.Div(id = 'sallen-explain', children = 'Choose values for c1 and r3 (reference schematic + design equations on left)'),
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
            ])
    elif design == 'Boctor Notch Lowpass':
        return html.Div(
            id='boctor-objs',
            children=[
                html.Div(id = 'boctor-explain', children='Choose values for r6, r5, and c1 (reference schematic + design equations on left)'),
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
            ])
    elif design == 'Multiple Feedback Lowpass':
        return html.Div(
            id='feedback-objs',
            children=[
                html.Div(id = 'feedback-explain', children='Choose value for c5 (reference schematic + design equations on left)'),
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
            ])
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

# #Sallen display
# @app.callback(
#     dash.dependencies.Output('sallen-display', 'children'),
#     [dash.dependencies.Input('sallen-values', 'children')]
# )
# def display_sallen(input):
#     displayParams = pd.read_json(input, orient='split')



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
    dash.dependencies.Output('r1-data', 'children'),
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
    dash.dependencies.Output('r1-prediction', 'children'),
    [dash.dependencies.Input('r1-data', 'children')],
    [dash.dependencies.State('gain-slider', 'value'),
     dash.dependencies.State('freq-slider', 'value')]
)
def display_prediction(value, input1, input2):
    return 'Set R1 to {0:.4f} for DC Gain of {1:.2f} dB and Cutoff Freq of {2:.2f} Hz'.format(value, get_db(input1),
                                                                                              10 ** input2)


@app.callback(
    dash.dependencies.Output('bode-value', 'children'),
    [dash.dependencies.Input('sim-button', 'n_clicks')],
    [dash.dependencies.State('design-selector', 'value'),
     dash.dependencies.State('tab-output', 'children')]
)
def on_click(n_clicks, design, input):
    if n_clicks > 0:

        if input['props']['id'] == 'ML-objs':
            designID, revisionID = SvApi.FindDesign(designObjs, design)
            simDesign = SvApi.GetDesign(designID, revisionID)
            simDesign = SvApi.CreateRevision(simDesign)
            simDesign = simDesign.json()

            #search for div holding r1
            search = 0
            while input['props']['children'][search]['props']['id'] != 'r1-data':
                search += 1
            r1 = input['props']['children'][search]['props']['children']


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

        if input['props']['id'] == 'equation-objs':
            if input['props']['children']['props']['id'] == 'sallen-objs':
                search = 0
                while (input['props']['children']['props']['children'][search]['props']['id'] != 'sallen-values'):
                    search += 1
                paramInputs = (input['props']['children']['props']['children'][search]['props']['children'])
                paramInputs = pd.read_json(paramInputs, orient='split')
                paramInputs = paramInputs.values
                designID, revisionID = SvApi.FindDesign(designObjs, design)
                simDesign = SvApi.GetDesign(designID, revisionID)
                simDesign = SvApi.CreateRevision(simDesign)
                simDesign = simDesign.json()
                for i in range (0,len(paramInputs)):
                        simDesign = SvApi.ChangeProperty(simDesign, paramInputs[i][0], paramInputs[i][1], paramInputs[i][2])
                        response = SvApi.PutDesign(simDesign)
                dfGain, dfPhase = SvApi.RunSallenKey()
                jsonGain = dfGain.to_json(orient='split')
                jsonPhase = dfPhase.to_json(orient='split')
            if input['props']['children']['props']['id'] == 'boctor-objs':
                search = 0
                while (input['props']['children']['props']['children'][search]['props']['id'] != 'boctor-values'):
                    search += 1
                paramInputs = (input['props']['children']['props']['children'][search]['props']['children'])
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
            if input['props']['children']['props']['id'] == 'feedback-objs':
                search = 0
                while (input['props']['children']['props']['children'][search]['props']['id'] != 'feedback-values'):
                    search += 1
                paramInputs = (input['props']['children']['props']['children'][search]['props']['children'])
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

if __name__ == '__main__':
    app.run_server()