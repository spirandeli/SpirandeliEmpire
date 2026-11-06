# syntax=docker/dockerfile:1.7
# Imagem única multi-stage: `app` (PHP-FPM) e `worker` (Supervisor).

ARG PHP_VERSION=8.3

# ------------------------------------------------------------------------------
# base: PHP + extensões obrigatórias
# (curl, openssl e mbstring já vêm compilados na imagem oficial)
# ------------------------------------------------------------------------------
FROM php:${PHP_VERSION}-fpm-bookworm AS base

ARG UID=1000
ARG GID=1000

ENV COMPOSER_ALLOW_SUPERUSER=1 \
    COMPOSER_HOME=/tmp/composer-cache \
    TZ=America/Sao_Paulo

RUN apt-get update && apt-get install -y --no-install-recommends \
        git unzip curl rsync ca-certificates default-mysql-client \
        libzip-dev libicu-dev libpng-dev libjpeg62-turbo-dev libfreetype6-dev \
        libcurl4-openssl-dev libssl-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j"$(nproc)" \
        pdo_mysql pcntl bcmath zip intl opcache gd exif sockets \
    && pecl install redis \
    && docker-php-ext-enable redis \
    && apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/pear

COPY --from=composer:2 /usr/bin/composer /usr/bin/composer

# www-data com o mesmo UID/GID do usuário do host (evita problemas de permissão nos volumes)
RUN groupmod -o -g ${GID} www-data && usermod -o -u ${UID} -g ${GID} www-data \
    && mkdir -p /var/www/html /tmp/composer-cache \
    && chown -R www-data:www-data /var/www/html /tmp/composer-cache

COPY docker/php/php.ini /usr/local/etc/php/conf.d/99-abvos.ini
COPY docker/php/www.conf /usr/local/etc/php-fpm.d/zz-abvos.conf

WORKDIR /var/www/html

# ------------------------------------------------------------------------------
# app: PHP-FPM servindo a API Laravel
# ------------------------------------------------------------------------------
FROM base AS app

COPY docker/php/entrypoint-app.sh /usr/local/bin/entrypoint-app
RUN chmod +x /usr/local/bin/entrypoint-app

EXPOSE 9000
ENTRYPOINT ["entrypoint-app"]
CMD ["php-fpm"]

# ------------------------------------------------------------------------------
# worker: Supervisor mantendo queue:work e schedule:work vivos
# ------------------------------------------------------------------------------
FROM base AS worker

RUN apt-get update && apt-get install -y --no-install-recommends supervisor procps \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/supervisor /var/run/supervisor

COPY docker/supervisor/supervisord.conf /etc/supervisor/supervisord.conf
COPY docker/php/entrypoint-worker.sh /usr/local/bin/entrypoint-worker
RUN chmod +x /usr/local/bin/entrypoint-worker

ENTRYPOINT ["entrypoint-worker"]
CMD ["supervisord", "-n", "-c", "/etc/supervisor/supervisord.conf"]
