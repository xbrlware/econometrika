library(RPostgreSQL)
driver <- PostgreSQL()
host <- Sys.getenv('HOST', 'localhost')
dbname <- Sys.getenv('DATABASE_NAME', 'econometrika')
dbuser <- Sys.getenv('DATABASE_USER')
dbpass <- Sys.getenv('DATABASE_PASSWORD')
con <- dbConnect(driver, host=host, dbname=dbname, user=dbuser, password=dbpass)

stmt <- dbSendQuery(con, "select sq.* from analysis_symbolquote sq join analysis_symbol sy on (sq.symbol_id = sy.id) where ticker = 'IBEX35' order by date")
ibex35 <- fetch(stmt, -1)
dbClearResult(stmt)
ibex35$rate <- c(0, log(tail(ibex35$close, -1)/head(ibex35$close, -1)))
library(plotly)
p <- ggplot(ibex35, aes(text=paste('Date: ', date, '\n', 'Compounding rate: ', round(rate, 4), '\n', 'Change: ', round(exp(rate)-1, 4)*100, '%', sep=''))) + geom_segment(aes(x=date, y=0, yend=rate, xend=date), size=0.2) + labs(x='Día', y='Ratio', caption=paste('Ratio de composición diario del IBEX35 desde ', head(ibex35$date, 1), ' hasta ', tail(ibex35$date, 1))) + theme(plot.caption = element_text(hjust = 0.5))
ply <- ggplotly(p, tooltip='text')
libpath <- file.path(getwd(), './media/plotly_lib')
wpath <- file.path(getwd(), './media/ibex35-daily-rate.html')
htmlwidgets::saveWidget(ply, wpath, libdir=libpath, selfcontained=F)
slug <- 'ibex35-daily-rate'
stmt <- postgresqlExecStatement(con, 'delete from analysis_plot where slug = $1', slug)
dbClearResult(stmt)
stmt <- postgresqlExecStatement(con, 'insert into analysis_plot (file_path, slug, title, lang_code_id, symbol_id, type, html_above, lib) values ($1, $2, $3, $4, $5, $6, $7, \'plotly\')',
    c(wpath, slug, 'Cambio diario del IBEX 35', 'es', head(ibex35$symbol_id, 1), 'statistic', ''))
dbClearResult(stmt)
ggsave('ibex35-daily-rate.png', p + theme(text = element_text(size=6)) + geom_text(hjust='right', data=subset(ibex35, rate %in% c(min(rate), max(rate))), size=1.5, aes(x=date, y=rate, label=paste(date, ': ', round(exp(rate)*100-100, 2), '% ', sep=''))), 'png', 'media', height=55, units=c("mm"))

# gaussian distribution: theoric no. ocurrences of drop > 1%, 3%, 5%, etc
mdg <- mean(ibex35$rate)
sdg <- sd(ibex35$rate)
libex35 <- length(ibex35$rate)
category <- 'analysis.non_normal_stock_returns'
stmt <- postgresqlExecStatement(con, 'delete from analysis_keyvalue where category = $1', c(category))
dbClearResult(stmt)
options("scipen"=-2, "digits"=4)
test <- shapiro.test(sample(ibex35$rate, 5000))
stmt <- postgresqlExecStatement(con, 'insert into analysis_keyvalue (category, key, value) values ($1, $2, $3)',
    c(category, 'last_ibex35_date', as.character(tail(ibex35$date, 1))))
dbClearResult(stmt)
stmt <- postgresqlExecStatement(con, 'insert into analysis_keyvalue (category, key, value) values ($1, $2, $3), ($4, $5, $6)',
    c(category, 'shapiro_wilk_test_p', prettyNum(test$p.value), category, 'shapiro_wilk_test_W', prettyNum(test$statistic)))
dbClearResult(stmt)
df <- data.frame(category=category, key=paste0('n_norm_drop_gt_', c('1pct', '3pct', '5pct', '7pct', '9pct', '11pct')), value=c(
    prettyNum(pnorm(log(0.99), mdg, sdg)*libex35),
    prettyNum(pnorm(log(0.97), mdg, sdg)*libex35),
    prettyNum(pnorm(log(0.95), mdg, sdg)*libex35),
    prettyNum(pnorm(log(0.93), mdg, sdg)*libex35),
    prettyNum(pnorm(log(0.91), mdg, sdg)*libex35),
    prettyNum(pnorm(log(0.89), mdg, sdg)*libex35)))
stmt <- dbSendQuery(con, 'copy analysis_keyvalue (category, key, value) from stdin')
postgresqlCopyInDataframe(con, df)
dbClearResult(stmt)

# actual no. ocurrences of drop > 1%, 2.5%, 5%, etc
df <- data.frame(category=category, key=paste0('n_observed_drop_gt_', c('1pct', '3pct', '5pct', '7pct', '9pct', '11pct')), value=c(
    prettyNum(sum(ibex35$rate < log(0.99))),
    prettyNum(sum(ibex35$rate < log(0.97))),
    prettyNum(sum(ibex35$rate < log(0.95))),
    prettyNum(sum(ibex35$rate < log(0.93))),
    prettyNum(sum(ibex35$rate < log(0.91))),
    prettyNum(sum(ibex35$rate < log(0.89)))))
stmt <- dbSendQuery(con, 'copy analysis_keyvalue (category, key, value) from stdin')
postgresqlCopyInDataframe(con, df)
dbClearResult(stmt)

p1 <- ggplot(ibex35, aes(rate)) + geom_histogram(bins=300, aes(y=..density.., fill=..count..)) + stat_function(fun=dnorm, aes(colour="Normal distribution"), args=list(mean=mdg, sd=sdg)) + scale_fill_continuous(guide = guide_legend(title = "Ratio de composición diario del IBEX35")) + scale_colour_manual(name=NULL, values=c("red")) + theme(legend.position="top")
p2 <- ggplot(ibex35, aes(sample = rate)) + stat_qq(color="orange", alpha=1) + geom_abline(intercept = mdg, slope = sdg)
sp <- subplot(p1, p2)
wpath <- file.path(getwd(), './media/ibex35-daily-rate-normality.html')
htmlwidgets::saveWidget(sp, wpath, libdir=libpath, selfcontained=F)
slug <- 'ibex35-daily-rate-normality'
stmt <- postgresqlExecStatement(con, 'delete from analysis_plot where slug = $1', slug)
dbClearResult(stmt)
stmt <- postgresqlExecStatement(con, 'insert into analysis_plot (file_path, slug, title, lang_code_id, symbol_id, type, html_above, lib) values ($1, $2, $3, $4, $5, $6, $7, \'plotly\')',
    c(wpath, slug, 'Retorno del IBEX 35 como distribución Normal', 'es', head(ibex35$symbol_id, 1), 'statistic', ''))
dbClearResult(stmt)
source('multiplot.R')
png('media/ibex35-daily-rate-normality.png', width=2100, units='px', height=649)
multiplot(p1 + theme(text = element_text(size=18)), p2 + theme(text = element_text(size=18)), cols=2)
dev.off()

mdl <- median(ibex35$rate)
sdl <- mad(ibex35$rate, constant=1)*sqrt(2)
library(rmutil)
p1 <- ggplot(ibex35, aes(rate)) + geom_histogram(bins=300, aes(y=..density.., fill=..count..)) + stat_function(fun=dlaplace, aes(colour="Laplace distribution"), args=list(m=mdl, s=sdl)) + scale_fill_continuous(guide = guide_legend(title = "Ratio diario del IBEX35")) + scale_colour_manual(name=NULL, values=c("red")) + theme(legend.position="top")
p2 <- ggplot(ibex35, aes(sample = rate)) + stat_qq(color="orange", alpha=1, distribution=qlaplace) + geom_abline(intercept = mdl, slope = sdl)
sp <- subplot(p1, p2)
wpath <- file.path(getwd(), './media/ibex35-daily-rate-laplacity.html')
htmlwidgets::saveWidget(sp, wpath, libdir=libpath, selfcontained=F)
slug <- 'ibex35-daily-rate-laplacity'
stmt <- postgresqlExecStatement(con, 'delete from analysis_plot where slug = $1', slug)
dbClearResult(stmt)
stmt <- postgresqlExecStatement(con, 'insert into analysis_plot (file_path, slug, title, lang_code_id, symbol_id, type, html_above, lib) values ($1, $2, $3, $4, $5, $6, $7, \'plotly\')',
    c(wpath, slug, 'Retorno del IBEX 35 como distribución de Laplace', 'es', head(ibex35$symbol_id, 1), 'statistic', ''))
dbClearResult(stmt)
png('media/ibex35-daily-rate-laplacity.png', width=2100, units='px', height=649)
multiplot(p1 + theme(text = element_text(size=18)), p2 + theme(text = element_text(size=18)), cols=2)
dev.off()

# laplace distribution: theoric no. ocurrences of drop > 1%, 2.5%, 5%, etc
df <- data.frame(category=category, key=paste0('n_laplace_drop_gt_', c('1pct', '3pct', '5pct', '7pct', '9pct', '11pct')), value=c(
     prettyNum(plaplace(log(0.99), mdl, sdl)*libex35),
     prettyNum(plaplace(log(0.97), mdl, sdl)*libex35),
     prettyNum(plaplace(log(0.95), mdl, sdl)*libex35),
     prettyNum(plaplace(log(0.93), mdl, sdl)*libex35),
     prettyNum(plaplace(log(0.91), mdl, sdl)*libex35),
     prettyNum(plaplace(log(0.89), mdl, sdl)*libex35)))
stmt <- dbSendQuery(con, 'copy analysis_keyvalue (category, key, value) from stdin')
postgresqlCopyInDataframe(con, df)
dbClearResult(stmt)
dbDisconnect(con)
