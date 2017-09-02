# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-07-28 11:52
from __future__ import unicode_literals

import os 
import csv
from django.db import migrations, models
from postgres_copy import CopyMapping
from django.core.management import call_command
import django.db.models.deletion
from analysis.models import Lang, Plot, Symbol, SymbolSource

def insertData(apps, schema_editor):
    lang = Lang(code='es', name='Español')
    lang.save()
    curdir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.normpath(os.path.join(curdir, os.pardir, os.pardir, 'data', 'mercado_continuo.csv'))
    c = CopyMapping(
        Symbol,
        path,
        dict(name='nombre', ticker='ticker'),
        static_mapping= {'market': 'Mercado Continuo', 'type': 'stock'}
    )
    c.save()
    Symbol(ticker='IBEX35', name='IBEX 35', market='Mercado Continuo', type=Symbol.INDEX).save()
    Symbol(ticker='IBEXTR', name='IBEX Total Return', market='Mercado Continuo', type=Symbol.INDEX).save()
    invertia_quote_tpl = 'https://www.invertia.com/es/mercados/bolsa/empresas/historico?p_p_id=cotizacioneshistoricas_WAR_ivfrontmarketsportlet&p_p_lifecycle=2&p_p_state=normal&p_p_mode=view&p_p_resource_id=exportExcel&p_p_cacheability=cacheLevelPage&p_p_col_id=column-1&p_p_col_pos=1&p_p_col_count=2&_cotizacioneshistoricas_WAR_ivfrontmarketsportlet_startDate={{startDate}}&_cotizacioneshistoricas_WAR_ivfrontmarketsportlet_endDate={{endDate}}&_cotizacioneshistoricas_WAR_ivfrontmarketsportlet_idtel={invertia_key}'
    invertia_dividend_tpl = 'https://www.invertia.com/es/mercados/bolsa/empresas/dividendos/-/empresa/{empresa}/{invertia_key}'
    curdir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.normpath(os.path.join(curdir, os.pardir, os.pardir, 'data', 'invertia_claves.csv'))
    invertia_keys = csv.reader(open(path))
    next(invertia_keys, None)  # skip the headers
    quote_sources = []
    for row in invertia_keys:
        quote_url = invertia_quote_tpl.format(invertia_key=row[2])
        dividend_url = invertia_dividend_tpl.format(empresa=row[1], invertia_key=row[2])
        try:
            symbol_id = Symbol.objects.get(ticker=row[0]).id
            SymbolSource(name='invertia', symbol_id=symbol_id, key=quote_url, type=SymbolSource.QUOTE).save()
            SymbolSource(name='invertia', symbol_id=symbol_id, key=dividend_url, type=SymbolSource.DIVIDEND).save()
        except Symbol.DoesNotExist:
            print('Symbol with ticker', row[0], "(%s)" % row[1], 'not found. Cotinuing...')
            continue
    mcs = Symbol.objects.filter(market='Mercado Continuo').exclude(ticker__in=('IBEX35', 'IBEXTR'))
    for symbol in mcs:
        SymbolSource(name='quantmod', symbol_id=symbol.id, key='%s.mc' % symbol.ticker, type=SymbolSource.SPLIT).save()

def runCommands(apps, schema_editor):
    call_command('import_splits')
    call_command('import_ohlcv_csv')
    #call_command('import_dividends')
    #call_command('fetch_dividends_invertia')
    #call_command('fetch_quotes_invertia')



class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Dividend',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pay_date', models.DateField(null=True)),
                ('ex_date', models.DateField()),
                ('gross', models.FloatField()),
                ('net', models.FloatField(null=True)),
                ('type', models.CharField(blank=True, max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='KeyValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(max_length=64)),
                ('key', models.CharField(max_length=64)),
                ('value', models.CharField(blank=True, max_length=256)),
            ],
        ),
        migrations.CreateModel(
            name='Lang',
            fields=[
                ('code', models.CharField(max_length=2, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=32)),
            ],
        ),
        migrations.CreateModel(
            name='Symbol',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ticker', models.CharField(max_length=8)),
                ('name', models.CharField(max_length=64)),
                ('market', models.CharField(max_length=64)),
                ('type', models.CharField(choices=[('index', 'Index'), ('bond', 'Bond'), ('stock', 'Stock'), ('fx', 'Foreign Exchange'), ('commodity', 'Commodity')], max_length=12)),
                ('adjusted_until', models.DateField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Plot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.CharField(max_length=64)),
                ('file_path', models.CharField(max_length=128)),
                ('title', models.CharField(max_length=64)),
                ('html_above', models.TextField(blank=True, default='')),
                ('lang_code', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analysis.Lang')),
                ('type', models.CharField(choices=[('statistic', 'Statistic'), ('quote', 'Quote')], max_length=12)),
                ('symbol', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='analysis.Symbol')),
            ],
        ),
        migrations.CreateModel(
            name='SymbolQuote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('open', models.FloatField(null=True)),
                ('high', models.FloatField(null=True)),
                ('low', models.FloatField(null=True)),
                ('close', models.FloatField()),
                ('close_unadj', models.FloatField(null=True)),
                ('volume', models.FloatField(null=True)),
                ('symbol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analysis.Symbol')),
            ],
        ),
        migrations.CreateModel(
            name='SymbolSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=32)),
                ('type', models.CharField(choices=[('dividend', 'Dividend'), ('quote', 'Quote')], max_length=12)),
                ('key', models.CharField(max_length=1024)),
                ('symbol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analysis.Symbol')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='symbolsource',
            unique_together=set([('type', 'name', 'symbol')]),
        ),
        migrations.AlterUniqueTogether(
            name='keyvalue',
            unique_together=set([('category', 'key')]),
        ),
        migrations.AddField(
            model_name='dividend',
            name='symbol',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='analysis.Symbol'),
        ),
        migrations.AlterUniqueTogether(
            name='symbolquote',
            unique_together=set([('symbol', 'date')]),
        ),
        migrations.AlterUniqueTogether(
            name='plot',
            unique_together=set([('lang_code', 'slug')]),
        ),
        migrations.CreateModel(
            name='Split',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('proportion', models.FloatField()),
                ('symbol', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='analysis.Symbol')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='split',
            unique_together=set([('symbol', 'date')]),
        ),
        migrations.AlterField(
            model_name='symbolsource',
            name='type',
            field=models.CharField(choices=[('dividend', 'Dividend'), ('quote', 'Quote'), ('quote', 'Split')], max_length=12),
        ),
        migrations.RunPython(insertData, lambda *args: None),
        migrations.RunPython(runCommands, lambda *args: None)
    ]
