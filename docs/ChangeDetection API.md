---
title: "changedetection.io API"
source: "https://changedetection.io/docs/api_v1/index.html#api-Watch-Create"
author:
published:
created: 2025-07-26
description: "Manage your changedetection.io watches via API, requires the `x-api-key` header which is found in the settings UI."
tags:
  - "clippings"
---
## Notifications

## Notifications | Create Notification URLs

Add one or more notification URLs from the configuration

post
```
/api/v1/notifications
```

```
curl http://localhost:5000/api/v1/notifications/batch -H"x-api-key:813031b16330fe25e3780cf0325daa45" -H "Content-Type: application/json" -d '{"notification_urls": ["url1", "url2"]}'
```

## 201

| Field | Type | Description |
| --- | --- | --- |
| notification\_urls | Object\[\] | List of added notification URLs |

## 400

| Name | Type | Description |
| --- | --- | --- |
| Invalid | String | input |

## Notifications | Delete Notification URLs

Deletes one or more notification URLs from the configuration

delete
```
/api/v1/notifications
```

```
curl http://localhost:5000/api/v1/notifications -X DELETE -H"x-api-key:813031b16330fe25e3780cf0325daa45" -H "Content-Type: application/json" -d '{"notification_urls": ["url1", "url2"]}'
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| notification\_urls | String\[\] | The notification URLs to delete. |

## 204

| Field | Type | Description |
| --- | --- | --- |
| OK | String | Deleted |

## 400

| Name | Type | Description |
| --- | --- | --- |
| No | String | matching notification URLs found. |

## Notifications | Replace Notification URLs

Replace all notification URLs with the provided list (can be empty)

put
```
/api/v1/notifications
```

```
curl -X PUT http://localhost:5000/api/v1/notifications -H"x-api-key:813031b16330fe25e3780cf0325daa45" -H "Content-Type: application/json" -d '{"notification_urls": ["url1", "url2"]}'
```

## 200

| Field | Type | Description |
| --- | --- | --- |
| notification\_urls | Object\[\] | List of current notification URLs |

## 400

| Name | Type | Description |
| --- | --- | --- |
| Invalid | String | input |

## Notifications | Return Notification URL List

Return the Notification URL List from the configuration

get
```
/api/v1/notifications
```

```
curl http://localhost:5000/api/v1/notifications -H"x-api-key:813031b16330fe25e3780cf0325daa45"
HTTP/1.0 200
{
    'notification_urls': ["notification-urls-list"]
}
```

## System Information

## System Information | Return system info

Return some info about the current system state

get
```
/api/v1/systeminfo
```

```
curl http://localhost:5000/api/v1/systeminfo -H"x-api-key:813031b16330fe25e3780cf0325daa45"
HTTP/1.0 200
{
    'queue_size': 10 ,
    'overdue_watches': ["watch-uuid-list"],
    'uptime': 38344.55,
    'watch_count': 800,
    'version': "0.40.1"
}
```

## Tag

## Tag | Create a single tag

post
```
/api/v1/watch
```

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | Was created |

## 500

| Field | Type | Description |
| --- | --- | --- |
| ERR | String | Some other error |

## Tag | Delete a tag and remove it from all watches

delete
```
/api/v1/tag/:uuid
```

```
curl http://localhost:5000/api/v1/tag/cc0cfffa-f449-477b-83ea-0caafd1dc091 -X DELETE -H"x-api-key:813031b16330fe25e3780cf0325daa45"
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| uuid | uuid | Tag unique ID. |

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | Was deleted |

## Tag | Single tag - get data or toggle notification muting.

Retrieve tag information and set notification\_muted status

get
```
/api/v1/tag/:uuid
```

```
curl http://localhost:5000/api/v1/tag/cc0cfffa-f449-477b-83ea-0caafd1dc091 -H"x-api-key:813031b16330fe25e3780cf0325daa45"
curl "http://localhost:5000/api/v1/tag/cc0cfffa-f449-477b-83ea-0caafd1dc091?muted=muted" -H"x-api-key:813031b16330fe25e3780cf0325daa45"
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| uuid | uuid | Tag unique ID. |

## Query Parameter(s)

| Field | Type | Description |
| --- | --- | --- |
| muted optional | String | \= `muted` or = `unmuted`, Sets the MUTE NOTIFICATIONS state |

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | When muted operation OR full JSON object of the tag |
| TagJSON | JSON | JSON Full JSON object of the tag |

## Tag | Update tag information

Updates an existing tag using JSON

put
```
/api/v1/tag/:uuid
```

```
Update (PUT)
curl http://localhost:5000/api/v1/tag/cc0cfffa-f449-477b-83ea-0caafd1dc091 -X PUT -H"x-api-key:813031b16330fe25e3780cf0325daa45" -H "Content-Type: application/json" -d '{"title": "New Tag Title"}'
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| uuid | uuid | Tag unique ID. |

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | Was updated |

## 500

| Field | Type | Description |
| --- | --- | --- |
| ERR | String | Some other error |

## Tag Management

## Tag Management | List tags

Return list of available tags

get
```
/api/v1/tags
```

```
curl http://localhost:5000/api/v1/tags -H"x-api-key:813031b16330fe25e3780cf0325daa45"
{
    "cc0cfffa-f449-477b-83ea-0caafd1dc091": {
        "title": "Tech News",
        "notification_muted": false,
        "date_created": 1677103794
    },
    "e6f5fd5c-dbfe-468b-b8f3-f9d6ff5ad69b": {
        "title": "Shopping",
        "notification_muted": true,
        "date_created": 1676662819
    }
}
```

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | JSON dict |

## Watch

## Watch | Create a single watch

Requires atleast `url` set, can accept the same structure as [get single watch information](https://changedetection.io/docs/api_v1/#api-Watch-Watch) to create.

post
```
/api/v1/watch
```

```
curl http://localhost:5000/api/v1/watch -H"x-api-key:813031b16330fe25e3780cf0325daa45" -H "Content-Type: application/json" -d '{"url": "https://my-nice.com" , "tag": "nice list"}'
```

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | Was created |

## 500

| Field | Type | Description |
| --- | --- | --- |
| ERR | String | Some other error |

delete
```
/api/v1/watch/:uuid
```

```
curl http://localhost:5000/api/v1/watch/cc0cfffa-f449-477b-83ea-0caafd1dc091 -X DELETE -H"x-api-key:813031b16330fe25e3780cf0325daa45"
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| uuid | uuid | Watch unique ID. |

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | Was deleted |

## Watch | Import a list of watched URLs

Accepts a line-feed separated list of URLs to import, additionally with?tag\_uuids=(tag id),?tag=(name),?proxy={key},?dedupe=true (default true) one URL per line.

post
```
/api/v1/import
```

```
curl http://localhost:5000/api/v1/import --data-binary @list-of-sites.txt -H"x-api-key:8a111a21bc2f8f1dd9b9353bbd46049a"
```

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | List | List of watch UUIDs added |

## 500

| Field | Type | Description |
| --- | --- | --- |
| ERR | String | Some other error |

## Watch | Single watch - get data, recheck, pause, mute.

Retrieve watch information and set muted/paused status

get
```
/api/v1/watch/:uuid
```

```
curl http://localhost:5000/api/v1/watch/cc0cfffa-f449-477b-83ea-0caafd1dc091  -H"x-api-key:813031b16330fe25e3780cf0325daa45"
curl "http://localhost:5000/api/v1/watch/cc0cfffa-f449-477b-83ea-0caafd1dc091?muted=unmuted"  -H"x-api-key:813031b16330fe25e3780cf0325daa45"
curl "http://localhost:5000/api/v1/watch/cc0cfffa-f449-477b-83ea-0caafd1dc091?paused=unpaused"  -H"x-api-key:813031b16330fe25e3780cf0325daa45"
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| uuid | uuid | Watch unique ID. |

## Query Parameter(s)

| Field | Type | Description |
| --- | --- | --- |
| recheck optional | Boolean | Recheck this watch `recheck=1` |
| paused optional | String | \= `paused` or = `unpaused`, Sets the PAUSED state |
| muted optional | String | \= `muted` or = `unmuted`, Sets the MUTE NOTIFICATIONS state |

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | When paused/muted/recheck operation OR full JSON object of the watch |
| WatchJSON | JSON | JSON Full JSON object of the watch |

## Watch | Update watch information

Updates an existing watch using JSON, accepts the same structure as returned in [get single watch information](https://changedetection.io/docs/api_v1/#api-Watch-Watch)

put
```
/api/v1/watch/:uuid
```

```
Update (PUT)
curl http://localhost:5000/api/v1/watch/cc0cfffa-f449-477b-83ea-0caafd1dc091 -X PUT -H"x-api-key:813031b16330fe25e3780cf0325daa45" -H "Content-Type: application/json" -d '{"url": "https://my-nice.com" , "tag": "new list"}'
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| uuid | uuid | Watch unique ID. |

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | Was updated |

## 500

| Field | Type | Description |
| --- | --- | --- |
| ERR | String | Some other error |

## Watch History

## Watch History | Get a list of all historical snapshots available for a watch

Requires `uuid`, returns list

get
```
/api/v1/watch/<string:uuid>/history
```

```
curl http://localhost:5000/api/v1/watch/cc0cfffa-f449-477b-83ea-0caafd1dc091/history -H"x-api-key:813031b16330fe25e3780cf0325daa45" -H "Content-Type: application/json"
{
    "1676649279": "/tmp/data/6a4b7d5c-fee4-4616-9f43-4ac97046b595/cb7e9be8258368262246910e6a2a4c30.txt",
    "1677092785": "/tmp/data/6a4b7d5c-fee4-4616-9f43-4ac97046b595/e20db368d6fc633e34f559ff67bb4044.txt",
    "1677103794": "/tmp/data/6a4b7d5c-fee4-4616-9f43-4ac97046b595/02efdd37dacdae96554a8cc85dc9c945.txt"
}
```

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String |  |

## 404

| Field | Type | Description |
| --- | --- | --- |
| ERR | String | Not found |

## Watch History | Get single snapshot from watch

Requires watch `uuid` and `timestamp`. `timestamp` of " `latest` " for latest available snapshot, or [use the list returned here](https://changedetection.io/docs/api_v1/#api-Watch_History-Get_list_of_available_stored_snapshots_for_watch)

get
```
/api/v1/watch/<string:uuid>/history/<int:timestamp>
```

```
curl http://localhost:5000/api/v1/watch/cc0cfffa-f449-477b-83ea-0caafd1dc091/history/1677092977 -H"x-api-key:813031b16330fe25e3780cf0325daa45" -H "Content-Type: application/json"
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| html optional | String | Optional Set to =1 to return the last HTML (only stores last 2 snapshots, use `latest` as timestamp) |

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String |  |

## 404

| Field | Type | Description |
| --- | --- | --- |
| ERR | String | Not found |

## Watch Management

## Watch Management | List watches

Return concise list of available watches and some very basic info

get
```
/api/v1/watch
```

```
curl http://localhost:5000/api/v1/watch -H"x-api-key:813031b16330fe25e3780cf0325daa45"
{
    "6a4b7d5c-fee4-4616-9f43-4ac97046b595": {
        "last_changed": 1677103794,
        "last_checked": 1677103794,
        "last_error": false,
        "title": "",
        "url": "http://www.quotationspage.com/random.php"
    },
    "e6f5fd5c-dbfe-468b-b8f3-f9d6ff5ad69b": {
        "last_changed": 0,
        "last_checked": 1676662819,
        "last_error": false,
        "title": "QuickLook",
        "url": "https://github.com/QL-Win/QuickLook/tags"
    }
}
```

## Parameter

| Field | Type | Description |
| --- | --- | --- |
| recheck\_all optional | String | Optional Set to =1 to force recheck of all watches |
| tag optional | String | Optional name of tag to limit results |

## 200

| Field | Type | Description |
| --- | --- | --- |
| OK | String | JSON dict |

Generated with [apidoc](https://apidocjs.com/) 0.54.0 - Sun Apr 13 2025 21:49:13 GMT+0200 (Central European Summer Time)