# Proxy

Author: Dmitry Podaruev (ddqof.vvv@gmail.com)

## Description

This is a proxy that forwards your http and https traffic with blacklist and
internet traffic restriction features.

## Requirements

You don't need to install any third-party packages.

## Examples of usage

* `./main.py` to run proxy at default (`8000`) port.
* `./main.py 9999` to run proxy at `9999` port.


## Features

All you need to enable any feature is to edit config file `proxy_config.py`. 

### Blacklist

To enable blacklist just add url to list under `black_list` key.  Adding
specific path is not supported.

#### Examples

To add youtube in blacklist you can type url with or without http scheme:

* `"black_list": ["youtube.com"]`

* `"black_list": ["https://www.youtube.com/"]`

Both statements will effect the same: add `youtube.com` in blacklist.

If resource you have added has **https** scheme then you will not receive any
banner that will notify you that this site is blocked, browser will only show
you `ERR_TUNNEL_CONNECTION_FAILED`. In case of **http** you will see
notification banner.

### Traffic restriction

To add restriction for specific resource you should add item to dict at
`restricted_resources` key. Key in this dict will be url and value will be
data limit for this resource.

#### Examples

To add restriction for 10 megabytes for youtube you can do this:

* `"restricted_resources": { "youtube.com":  10 * 1_000_000}`

* `"restricted_resources": { "https://www.youtube.com/":  10 * 1_000_000}`

Both statemenets will effect the same.

Like in blacklist feature, you will see notification banner only if site you
have been added has **http** scheme, otherwise there will be error
`ERR_CONNECTION_CLOSED`.

#### Accuracy

Restriction accuracy cannot be 100% for any high-load services like
**vk.com** or **youtube.com** but proxy catches major part of traffic from these resources.
With other websites this proxy cannot ensure that this feature will count
major part of traffic too. Use this feature if you sure that resource you want to
restrict doesn't send requests to many other resources.