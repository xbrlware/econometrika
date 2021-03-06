# -*- coding: utf-8 -*-
#from __future__ import unicode_literals
import os
from django.shortcuts import render
#from django.templatetags.static import static
from django.conf.urls.static import static
from django.conf import settings
from datetime import datetime
from django.http import HttpResponse
from analysis.models import KeyValue, Plot, Symbol, SymbolQuote, PeriodReturn
from dal import autocomplete
from collections import OrderedDict
import locale

def non_normal_stock_returns(request):
    context = {'analysis_page': True}
    category = 'analysis.non_normal_stock_returns'
    k = 'last_ibex35_date'
    context[k] = datetime.strptime(KeyValue.objects.get(category=category, key=k).value, '%Y-%m-%d').date()
    keys = [item for sublist in [['shapiro_wilk_test_W', 'shapiro_wilk_test_p']] + [prefix.join(\
        ['', '1pct,', '3pct,', '5pct,', '7pct,', '9pct,', '11pct']).split(',') for prefix in ['n_norm_drop_gt_', 'n_observed_drop_gt_', 'n_laplace_drop_gt_']]\
            for item in sublist]
    for k in keys:
        context[k] = KeyValue.objects.get(category=category, key=k).value
    return render(request, 'analysis/non-normal-stock-returns.html', context)

from django import template

register = template.Library()

@register.filter
def get_value(dict_name, key_name):
    return dict_name.get(key_name, '')

def stock_returns_tolerance_limits(request):
    context = {'analysis_page': True}
    keys = ['last_ibex35_date', 'ibex35_max_drop_date', 'ibex35_max_gain_date']
    category = 'analysis.stock-returns-tolerance-limits'
    for k in keys:
        context[k] = datetime.strptime(KeyValue.objects.get(category=category, key=k).value, '%Y-%m-%d').date()

    keys = ['ibex35_max_drop', 'ibex35_max_gain', 'ibex35_0.999_bitol_D', 'ibex35_0.99_bitol_D', 'ibex35_0.999_unitol_D', 'ibex35_0.99_unitol_D']
    for k in keys:
        context[k.replace('.', '_')] = float(KeyValue.objects.get(category=category, key=k).value)

    context['ibex35_n_observations'] = int(KeyValue.objects.get(category=category, key='ibex35_n_observations').value)
    context['ibex35_0_999_bitol_per_10mille'] = int(10000 - context['ibex35_0_999_bitol_D'] * 10000)
    context['ibex35_0_999_bitol_per_sample'] = round((10000 - context['ibex35_0_999_bitol_D'] * 10000) / 10000 * context['ibex35_n_observations'])
    context['ibex35_0_99_bitol_per_10mille'] = int(10000 - context['ibex35_0_99_bitol_D'] * 10000)
    context['ibex35_0_99_bitol_per_sample'] = round((10000 - context['ibex35_0_99_bitol_D'] * 10000) / 10000 * context['ibex35_n_observations'])
    context['ibex35_0_999_unitol_per_10mille'] = int(10000 - context['ibex35_0_999_unitol_D'] * 10000)
    context['ibex35_0_999_unitol_per_sample'] = round((10000 - context['ibex35_0_999_unitol_D'] * 10000) / 10000 * context['ibex35_n_observations'])
    context['ibex35_0_99_unitol_per_10mille'] = int(10000 - context['ibex35_0_99_unitol_D'] * 10000)
    context['ibex35_0_99_unitol_per_sample'] = round((10000 - context['ibex35_0_99_unitol_D'] * 10000) / 10000 * context['ibex35_n_observations'])
    return render(request, 'analysis/stock-returns-tolerance-limits.html', context)
    
def plot(request, name):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    plot = Plot.objects.get(slug=name)
    if plot.symbol_id:
        symbol = Symbol.objects.get(id=plot.symbol_id)
        last_two_quotes = SymbolQuote.objects.filter(symbol_id=plot.symbol_id).order_by('-date')[:2]
        last_pct_change = round((last_two_quotes[0].close / last_two_quotes[1].close - 1) * 100, 2)
        last_quote = last_two_quotes[0].close
    else:
        last_pct_change = last_quote = None
    fragment = open(plot.file_path, 'rb').read().decode('UTF-8')
    title = plot.title
    html_above = plot.html_above
    if plot.lib == 'dygraphs':
        return render(request, 'analysis/plot_dy.html', {'fragment': fragment, 'title': title, 'html_above': html_above, 'plot_page': True, 'container_fluid': True, 'last_quote': last_quote, 'last_pct_change': last_pct_change, 'ticker': symbol.ticker})
    else: # plotly
        srcdoc = fragment.replace('plotly_lib', '/media/plotly_lib')
        return render(request, 'analysis/plot_ly.html', {'srcdoc': srcdoc, 'title': title, 'html_above': html_above, 'plot_page': True, 'container_fluid': True})

class SymbolAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = Symbol.objects.all()
        if self.q:
            qs = qs.filter(name__icontains=self.q) | qs.filter(ticker__istartswith=self.q)

        return qs

    def get_result_value(self, result):
        return result.ticker

def winners_losers(request):
    period_returns = PeriodReturn.objects.select_related('symbol').order_by('-period_return').all()
    period_returns_odict = OrderedDict([
        ('1D', []),
        ('1W', []),
        ('1M', []),
        ('3M', []),
        ('6M', []),
        ('YTD', []),
        ('1Y', []),
    ])
    for perret in period_returns:
        period_returns_odict[perret.period_type].append((perret.symbol.ticker,
            {'name': perret.symbol.name, 'return': round(perret.period_return * 100, 2)}))

    for perret in period_returns:
        period_returns_odict[perret.period_type] = OrderedDict(period_returns_odict[perret.period_type])

    return render(request, 'analysis/winners_losers.html', {'period_returns': period_returns_odict})
