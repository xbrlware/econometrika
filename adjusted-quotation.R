library(RPostgreSQL)
driver <- PostgreSQL()
host <- Sys.getenv('HOST', 'localhost')
dbname <- Sys.getenv('DATABASE_NAME', 'econometrika')
dbuser <- Sys.getenv('DATABASE_USER')
dbpass <- Sys.getenv('DATABASE_PASSWORD')
con <- dbConnect(driver, host=host, dbname=dbname, user=dbuser, password=dbpass)

stmt <- dbSendQuery(con, "select * from analysis_split order by date desc")
splits <- fetch(stmt, -1)
dbClearResult(stmt)

args <- commandArgs(trailingOnly=T)
if (length(args) > 0) {
    stmt <- dbSendQuery(con, "select * from analysis_symbol where ticker = $1", args[1])
} else {
    stmt <- dbSendQuery(con, "select * from analysis_symbol")
}
symbols <- fetch(stmt, -1)
dbClearResult(stmt)

library(dygraphs)
library(htmltools)
library(knitr)
library(TTR)
library(xts)
bpath <- './media/'
for (rs in rownames(symbols)) {
    symbol <- symbols[rs,]
    stmt <- dbSendQuery(con, "select sq.* from analysis_symbolquote sq where sq.symbol_id  = $1 order by date", symbol$id)
    quotes <- fetch(stmt, -1)
    dbClearResult(stmt)
    if (nrow(quotes) == 0) next
    print(paste0('Generating for ', symbol$name))
    date <- quotes$date
    quotes <- xts(quotes[, c('open', 'high', 'low', 'close', 'volume')], quotes$date)
    colnames(quotes) <- c('Open', 'High', 'Low', 'Close', 'Volume')
    if (length(quotes$Close) > 50) {
        bbands <- BBands(quotes[, c('High', 'Low', 'Close')], 50, sd=2.1)
        quotes <- cbind(quotes, bbands)
        dyg1 <- dygraph(quotes[, c('Close', 'up', 'dn', 'mavg')], width='100%', height='400px', group='symbol', ylab='Cotización (€)') %>%
            dySeries(c('dn', 'Close', 'up'), strokeWidth=1, label='Cierre') %>%
            dySeries(c('mavg'), strokeWidth=0.5, label='Media móvil')
    }
    else dyg1 <- dygraph(quotes[, c('Close')], width='100%', height='400px', group='symbol', ylab='Cotización (€)') %>%
        dySeries(c('Close'), strokeWidth=1, label='Cierre')
    dyg1 <- dyg1 %>% dyOptions(colors = RColorBrewer::brewer.pal(3, 'Set2'), mobileDisableYTouch=TRUE)
    dyg2 <- dygraph(quotes[,'Volume'], width='100%', height='150px', group='symbol', ylab='Nº acciones') %>%
        dySeries('Volume', label='Volumen') %>%
        dyRangeSelector() %>%
        dyOptions(fillGraph=TRUE, fillAlpha=0.7, colors=RColorBrewer::brewer.pal(4, 'Set2')[3:4], mobileDisableYTouch=TRUE)
    slug <- paste0(tolower(symbol$ticker), '-adjusted-quote')
    wpath <- file.path(getwd(), bpath, paste0(slug, '.html'))
    knit(text='<!--begin.rcode echo=F
        tagList(dyg1)
        tagList(dyg2)
    end.rcode-->', output=wpath)
    stmt <- postgresqlExecStatement(con, 'delete from analysis_plot where slug = $1', slug)
    dbClearResult(stmt)
    stmt <- postgresqlExecStatement(con, 'insert into analysis_plot (file_path, slug, title, lang_code_id, symbol_id, type, html_above, lib) values ($1, $2, $3, $4, $5, $6, $7, \'dygraphs\')',
        c(wpath, slug, paste0(substring(symbol$name, 1, 42), ': cotización ajustada'), 'es', symbol$id, 'quote', ''))
    dbClearResult(stmt)
    print(paste0('Done with ', symbol$name))
}
dbDisconnect(con)
