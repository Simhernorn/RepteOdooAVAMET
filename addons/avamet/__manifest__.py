# -*- coding: utf-8 -*-
{
    'name': "AVAMET Weather Data",

    'summary': "Registres meteorològics i de càmera d'AVAMET",

    'description': """
Gestió de lectures meteorològiques, imatges de càmera i resums diaris d'AVAMET.
    """,

    'author': "AVAMET",
    'category': 'Services',
    'version': '18.0.1.0.0',

    'depends': ['base'],

    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    'demo': [
        'demo/demo_reading.csv',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

