from langchain_core.messages import AIMessage, ToolMessage

mpc_response = {
    "messages": [
        AIMessage(
            content="",
            additional_kwargs={
                "tool_calls": [
                    {
                        "index": 0,
                        "id": "call_HG5Xriy64Ddn5CbAtUVPtsv4",
                        "function": {"arguments": "{}", "name": "get_devices"},
                        "type": "function",
                    }
                ]
            },
            response_metadata={
                "finish_reason": "tool_calls",
                "model_name": "gpt-5-nano-2025-08-07",
                "service_tier": "default",
            },
            id="run--77283b26-b0c2-4484-b5e9-c2135806ce51",
            tool_calls=[
                {
                    "name": "get_devices",
                    "args": {},
                    "id": "call_HG5Xriy64Ddn5CbAtUVPtsv4",
                    "type": "tool_call",
                }
            ],
        ),
        ToolMessage(
            content='{\n  "devices": [\n    {\n      "name": "xrd-1",\n      "ip_address": "10.10.20.101",\n      "port": 57777,\n      "nos": "iosxr",\n      "username": "cisco",\n      "password": "***",\n      "path_cert": null,\n      "path_key": null,\n      "path_root": null,\n      "override": null,\n      "skip_verify": false,\n      "gnmi_timeout": 5,\n      "grpc_options": null,\n      "show_diff": null,\n      "insecure": true\n    },\n    {\n      "name": "xrd-2",\n      "ip_address": "10.10.20.102",\n      "port": 57777,\n      "nos": "iosxr",\n      "username": "cisco",\n      "password": "***",\n      "path_cert": null,\n      "path_key": null,\n      "path_root": null,\n      "override": null,\n      "skip_verify": false,\n      "gnmi_timeout": 5,\n      "grpc_options": null,\n      "show_diff": null,\n      "insecure": true\n    },\n    {\n      "name": "xrd-3",\n      "ip_address": "10.10.20.103",\n      "port": 57777,\n      "nos": "iosxr",\n      "username": "cisco",\n      "password": "***",\n      "path_cert": null,\n      "path_key": null,\n      "path_root": null,\n      "override": null,\n      "skip_verify": false,\n      "gnmi_timeout": 5,\n      "grpc_options": null,\n      "show_diff": null,\n      "insecure": true\n    },\n    {\n      "name": "xrd-4",\n      "ip_address": "10.10.20.104",\n      "port": 57777,\n      "nos": "iosxr",\n      "username": "cisco",\n      "password": "***",\n      "path_cert": null,\n      "path_key": null,\n      "path_root": null,\n      "override": null,\n      "skip_verify": false,\n      "gnmi_timeout": 5,\n      "grpc_options": null,\n      "show_diff": null,\n      "insecure": true\n    },\n    {\n      "name": "xrd-5",\n      "ip_address": "10.10.20.105",\n      "port": 57777,\n      "nos": "iosxr",\n      "username": "cisco",\n      "password": "***",\n      "path_cert": null,\n      "path_key": null,\n      "path_root": null,\n      "override": null,\n      "skip_verify": false,\n      "gnmi_timeout": 5,\n      "grpc_options": null,\n      "show_diff": null,\n      "insecure": true\n    },\n    {\n      "name": "xrd-6",\n      "ip_address": "10.10.20.106",\n      "port": 57777,\n      "nos": "iosxr",\n      "username": "cisco",\n      "password": "***",\n      "path_cert": null,\n      "path_key": null,\n      "path_root": null,\n      "override": null,\n      "skip_verify": false,\n      "gnmi_timeout": 5,\n      "grpc_options": null,\n      "show_diff": null,\n      "insecure": true\n    },\n    {\n      "name": "xrd-7",\n      "ip_address": "10.10.20.107",\n      "port": 57777,\n      "nos": "iosxr",\n      "username": "cisco",\n      "password": "***",\n      "path_cert": null,\n      "path_key": null,\n      "path_root": null,\n      "override": null,\n      "skip_verify": false,\n      "gnmi_timeout": 5,\n      "grpc_options": null,\n      "show_diff": null,\n      "insecure": true\n    },\n    {\n      "name": "xrd-8",\n      "ip_address": "10.10.20.108",\n      "port": 57777,\n      "nos": "iosxr",\n      "username": "cisco",\n      "password": "***",\n      "path_cert": null,\n      "path_key": null,\n      "path_root": null,\n      "override": null,\n      "skip_verify": false,\n      "gnmi_timeout": 5,\n      "grpc_options": null,\n      "show_diff": null,\n      "insecure": true\n    }\n  ]\n}',
            name="get_devices",
            id="44c9147e-58d7-49ed-854e-7cbbeec060d6",
            tool_call_id="call_HG5Xriy64Ddn5CbAtUVPtsv4",
        ),
        AIMessage(
            content='{\n  "device_name": "xrd-1"\n}',
            additional_kwargs={},
            response_metadata={
                "finish_reason": "stop",
                "model_name": "gpt-5-nano-2025-08-07",
                "service_tier": "default",
            },
            id="run--8c7efea9-6655-4e20-a704-3415288d232d",
        ),
    ]
}
