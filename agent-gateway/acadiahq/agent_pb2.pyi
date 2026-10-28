from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AgentFrame(_message.Message):
    __slots__ = ("pairing_handshake", "heartbeat", "telemetry_batch", "fault_event", "log_upload_request", "command_ack", "upload_complete")
    PAIRING_HANDSHAKE_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    TELEMETRY_BATCH_FIELD_NUMBER: _ClassVar[int]
    FAULT_EVENT_FIELD_NUMBER: _ClassVar[int]
    LOG_UPLOAD_REQUEST_FIELD_NUMBER: _ClassVar[int]
    COMMAND_ACK_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    pairing_handshake: PairingHandshake
    heartbeat: Heartbeat
    telemetry_batch: TelemetryBatch
    fault_event: FaultEvent
    log_upload_request: LogUploadRequest
    command_ack: CommandAck
    upload_complete: UploadComplete
    def __init__(self, pairing_handshake: _Optional[_Union[PairingHandshake, _Mapping]] = ..., heartbeat: _Optional[_Union[Heartbeat, _Mapping]] = ..., telemetry_batch: _Optional[_Union[TelemetryBatch, _Mapping]] = ..., fault_event: _Optional[_Union[FaultEvent, _Mapping]] = ..., log_upload_request: _Optional[_Union[LogUploadRequest, _Mapping]] = ..., command_ack: _Optional[_Union[CommandAck, _Mapping]] = ..., upload_complete: _Optional[_Union[UploadComplete, _Mapping]] = ...) -> None: ...

class PairingHandshake(_message.Message):
    __slots__ = ("pairing_token",)
    PAIRING_TOKEN_FIELD_NUMBER: _ClassVar[int]
    pairing_token: str
    def __init__(self, pairing_token: _Optional[str] = ...) -> None: ...

class Heartbeat(_message.Message):
    __slots__ = ("device_id", "credential_token", "sent_at_unix_ms", "agent_version", "protocol_version", "boot_id", "heartbeat_sequence", "sent_at_mono_ns", "capabilities", "status")
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TOKEN_FIELD_NUMBER: _ClassVar[int]
    SENT_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    AGENT_VERSION_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_VERSION_FIELD_NUMBER: _ClassVar[int]
    BOOT_ID_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_SEQUENCE_FIELD_NUMBER: _ClassVar[int]
    SENT_AT_MONO_NS_FIELD_NUMBER: _ClassVar[int]
    CAPABILITIES_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    device_id: str
    credential_token: str
    sent_at_unix_ms: int
    agent_version: str
    protocol_version: int
    boot_id: str
    heartbeat_sequence: int
    sent_at_mono_ns: int
    capabilities: _containers.RepeatedScalarFieldContainer[str]
    status: DeviceStatus
    def __init__(self, device_id: _Optional[str] = ..., credential_token: _Optional[str] = ..., sent_at_unix_ms: _Optional[int] = ..., agent_version: _Optional[str] = ..., protocol_version: _Optional[int] = ..., boot_id: _Optional[str] = ..., heartbeat_sequence: _Optional[int] = ..., sent_at_mono_ns: _Optional[int] = ..., capabilities: _Optional[_Iterable[str]] = ..., status: _Optional[_Union[DeviceStatus, _Mapping]] = ...) -> None: ...

class DeviceStatus(_message.Message):
    __slots__ = ("image_version", "running_slot", "slot_confirmed", "component_versions", "health_known", "health_score", "time_synchronized", "services", "serial", "hardware_revision", "istate_state", "collected_at_unix_ms")
    class ComponentVersionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    IMAGE_VERSION_FIELD_NUMBER: _ClassVar[int]
    RUNNING_SLOT_FIELD_NUMBER: _ClassVar[int]
    SLOT_CONFIRMED_FIELD_NUMBER: _ClassVar[int]
    COMPONENT_VERSIONS_FIELD_NUMBER: _ClassVar[int]
    HEALTH_KNOWN_FIELD_NUMBER: _ClassVar[int]
    HEALTH_SCORE_FIELD_NUMBER: _ClassVar[int]
    TIME_SYNCHRONIZED_FIELD_NUMBER: _ClassVar[int]
    SERVICES_FIELD_NUMBER: _ClassVar[int]
    SERIAL_FIELD_NUMBER: _ClassVar[int]
    HARDWARE_REVISION_FIELD_NUMBER: _ClassVar[int]
    ISTATE_STATE_FIELD_NUMBER: _ClassVar[int]
    COLLECTED_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    image_version: str
    running_slot: str
    slot_confirmed: bool
    component_versions: _containers.ScalarMap[str, str]
    health_known: bool
    health_score: float
    time_synchronized: bool
    services: _containers.RepeatedCompositeFieldContainer[ServiceState]
    serial: str
    hardware_revision: str
    istate_state: str
    collected_at_unix_ms: int
    def __init__(self, image_version: _Optional[str] = ..., running_slot: _Optional[str] = ..., slot_confirmed: _Optional[bool] = ..., component_versions: _Optional[_Mapping[str, str]] = ..., health_known: _Optional[bool] = ..., health_score: _Optional[float] = ..., time_synchronized: _Optional[bool] = ..., services: _Optional[_Iterable[_Union[ServiceState, _Mapping]]] = ..., serial: _Optional[str] = ..., hardware_revision: _Optional[str] = ..., istate_state: _Optional[str] = ..., collected_at_unix_ms: _Optional[int] = ...) -> None: ...

class ServiceState(_message.Message):
    __slots__ = ("unit", "active")
    UNIT_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_FIELD_NUMBER: _ClassVar[int]
    unit: str
    active: str
    def __init__(self, unit: _Optional[str] = ..., active: _Optional[str] = ...) -> None: ...

class TelemetryBatch(_message.Message):
    __slots__ = ("samples", "location")
    SAMPLES_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    samples: _containers.RepeatedCompositeFieldContainer[TelemetrySample]
    location: Location
    def __init__(self, samples: _Optional[_Iterable[_Union[TelemetrySample, _Mapping]]] = ..., location: _Optional[_Union[Location, _Mapping]] = ...) -> None: ...

class TelemetrySample(_message.Message):
    __slots__ = ("metric", "value", "recorded_at_unix_ms", "tags")
    class TagsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    METRIC_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    metric: str
    value: float
    recorded_at_unix_ms: int
    tags: _containers.ScalarMap[str, str]
    def __init__(self, metric: _Optional[str] = ..., value: _Optional[float] = ..., recorded_at_unix_ms: _Optional[int] = ..., tags: _Optional[_Mapping[str, str]] = ...) -> None: ...

class Location(_message.Message):
    __slots__ = ("lat", "lon", "accuracy_m", "source", "recorded_at_unix_ms")
    class Source(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        UNKNOWN: _ClassVar[Location.Source]
        GNSS: _ClassVar[Location.Source]
        NETWORK: _ClassVar[Location.Source]
    UNKNOWN: Location.Source
    GNSS: Location.Source
    NETWORK: Location.Source
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    ACCURACY_M_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    RECORDED_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    accuracy_m: float
    source: Location.Source
    recorded_at_unix_ms: int
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ..., accuracy_m: _Optional[float] = ..., source: _Optional[_Union[Location.Source, str]] = ..., recorded_at_unix_ms: _Optional[int] = ...) -> None: ...

class FaultEvent(_message.Message):
    __slots__ = ("code", "severity", "message", "kind", "at_unix_ms", "fault_code_ref")
    class Severity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        INFO: _ClassVar[FaultEvent.Severity]
        WARN: _ClassVar[FaultEvent.Severity]
        CRITICAL: _ClassVar[FaultEvent.Severity]
    INFO: FaultEvent.Severity
    WARN: FaultEvent.Severity
    CRITICAL: FaultEvent.Severity
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        RAISED: _ClassVar[FaultEvent.Kind]
        CLEARED: _ClassVar[FaultEvent.Kind]
    RAISED: FaultEvent.Kind
    CLEARED: FaultEvent.Kind
    CODE_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    FAULT_CODE_REF_FIELD_NUMBER: _ClassVar[int]
    code: str
    severity: FaultEvent.Severity
    message: str
    kind: FaultEvent.Kind
    at_unix_ms: int
    fault_code_ref: str
    def __init__(self, code: _Optional[str] = ..., severity: _Optional[_Union[FaultEvent.Severity, str]] = ..., message: _Optional[str] = ..., kind: _Optional[_Union[FaultEvent.Kind, str]] = ..., at_unix_ms: _Optional[int] = ..., fault_code_ref: _Optional[str] = ...) -> None: ...

class LogUploadRequest(_message.Message):
    __slots__ = ("kind", "time_range_start_unix_ms", "time_range_end_unix_ms", "size_bytes_estimate", "client_ref")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        LOG_BUNDLE: _ClassVar[LogUploadRequest.Kind]
        BACKUP: _ClassVar[LogUploadRequest.Kind]
    LOG_BUNDLE: LogUploadRequest.Kind
    BACKUP: LogUploadRequest.Kind
    KIND_FIELD_NUMBER: _ClassVar[int]
    TIME_RANGE_START_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    TIME_RANGE_END_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_ESTIMATE_FIELD_NUMBER: _ClassVar[int]
    CLIENT_REF_FIELD_NUMBER: _ClassVar[int]
    kind: LogUploadRequest.Kind
    time_range_start_unix_ms: int
    time_range_end_unix_ms: int
    size_bytes_estimate: int
    client_ref: str
    def __init__(self, kind: _Optional[_Union[LogUploadRequest.Kind, str]] = ..., time_range_start_unix_ms: _Optional[int] = ..., time_range_end_unix_ms: _Optional[int] = ..., size_bytes_estimate: _Optional[int] = ..., client_ref: _Optional[str] = ...) -> None: ...

class UploadComplete(_message.Message):
    __slots__ = ("request_ref", "success", "size_bytes", "sha256", "error")
    REQUEST_REF_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SIZE_BYTES_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    request_ref: str
    success: bool
    size_bytes: int
    sha256: str
    error: str
    def __init__(self, request_ref: _Optional[str] = ..., success: _Optional[bool] = ..., size_bytes: _Optional[int] = ..., sha256: _Optional[str] = ..., error: _Optional[str] = ...) -> None: ...

class CommandAck(_message.Message):
    __slots__ = ("command_id", "success", "error", "daemon", "operation", "code", "json_payload", "correlation_id", "accepted_at_mono_ns", "completed_at_mono_ns", "retryable")
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    DAEMON_FIELD_NUMBER: _ClassVar[int]
    OPERATION_FIELD_NUMBER: _ClassVar[int]
    CODE_FIELD_NUMBER: _ClassVar[int]
    JSON_PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    ACCEPTED_AT_MONO_NS_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_AT_MONO_NS_FIELD_NUMBER: _ClassVar[int]
    RETRYABLE_FIELD_NUMBER: _ClassVar[int]
    command_id: str
    success: bool
    error: str
    daemon: str
    operation: str
    code: str
    json_payload: str
    correlation_id: str
    accepted_at_mono_ns: int
    completed_at_mono_ns: int
    retryable: bool
    def __init__(self, command_id: _Optional[str] = ..., success: _Optional[bool] = ..., error: _Optional[str] = ..., daemon: _Optional[str] = ..., operation: _Optional[str] = ..., code: _Optional[str] = ..., json_payload: _Optional[str] = ..., correlation_id: _Optional[str] = ..., accepted_at_mono_ns: _Optional[int] = ..., completed_at_mono_ns: _Optional[int] = ..., retryable: _Optional[bool] = ...) -> None: ...

class ServerFrame(_message.Message):
    __slots__ = ("pairing_result", "heartbeat_ack", "command", "signed_upload_url")
    PAIRING_RESULT_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_ACK_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    SIGNED_UPLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    pairing_result: PairingResult
    heartbeat_ack: HeartbeatAck
    command: Command
    signed_upload_url: SignedUploadUrl
    def __init__(self, pairing_result: _Optional[_Union[PairingResult, _Mapping]] = ..., heartbeat_ack: _Optional[_Union[HeartbeatAck, _Mapping]] = ..., command: _Optional[_Union[Command, _Mapping]] = ..., signed_upload_url: _Optional[_Union[SignedUploadUrl, _Mapping]] = ...) -> None: ...

class PairingResult(_message.Message):
    __slots__ = ("success", "error", "device_id", "credential_token", "credential_expires_at_unix_ms")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    DEVICE_ID_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_TOKEN_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_EXPIRES_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error: str
    device_id: str
    credential_token: str
    credential_expires_at_unix_ms: int
    def __init__(self, success: _Optional[bool] = ..., error: _Optional[str] = ..., device_id: _Optional[str] = ..., credential_token: _Optional[str] = ..., credential_expires_at_unix_ms: _Optional[int] = ...) -> None: ...

class HeartbeatAck(_message.Message):
    __slots__ = ("server_time_unix_ms", "next_heartbeat_interval_s", "protocol_version", "renewed_credential_token", "credential_expires_at_unix_ms")
    SERVER_TIME_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    NEXT_HEARTBEAT_INTERVAL_S_FIELD_NUMBER: _ClassVar[int]
    PROTOCOL_VERSION_FIELD_NUMBER: _ClassVar[int]
    RENEWED_CREDENTIAL_TOKEN_FIELD_NUMBER: _ClassVar[int]
    CREDENTIAL_EXPIRES_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    server_time_unix_ms: int
    next_heartbeat_interval_s: int
    protocol_version: int
    renewed_credential_token: str
    credential_expires_at_unix_ms: int
    def __init__(self, server_time_unix_ms: _Optional[int] = ..., next_heartbeat_interval_s: _Optional[int] = ..., protocol_version: _Optional[int] = ..., renewed_credential_token: _Optional[str] = ..., credential_expires_at_unix_ms: _Optional[int] = ...) -> None: ...

class Command(_message.Message):
    __slots__ = ("command_id", "take_backup_now", "restore", "factory_reset", "apply_update", "operation", "daemon", "json_args", "actor", "deadline_ms", "idempotency_key", "correlation_id", "required_confirmation")
    COMMAND_ID_FIELD_NUMBER: _ClassVar[int]
    TAKE_BACKUP_NOW_FIELD_NUMBER: _ClassVar[int]
    RESTORE_FIELD_NUMBER: _ClassVar[int]
    FACTORY_RESET_FIELD_NUMBER: _ClassVar[int]
    APPLY_UPDATE_FIELD_NUMBER: _ClassVar[int]
    OPERATION_FIELD_NUMBER: _ClassVar[int]
    DAEMON_FIELD_NUMBER: _ClassVar[int]
    JSON_ARGS_FIELD_NUMBER: _ClassVar[int]
    ACTOR_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_MS_FIELD_NUMBER: _ClassVar[int]
    IDEMPOTENCY_KEY_FIELD_NUMBER: _ClassVar[int]
    CORRELATION_ID_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_CONFIRMATION_FIELD_NUMBER: _ClassVar[int]
    command_id: str
    take_backup_now: TakeBackupNow
    restore: Restore
    factory_reset: FactoryReset
    apply_update: ApplyUpdate
    operation: str
    daemon: str
    json_args: str
    actor: str
    deadline_ms: int
    idempotency_key: str
    correlation_id: str
    required_confirmation: str
    def __init__(self, command_id: _Optional[str] = ..., take_backup_now: _Optional[_Union[TakeBackupNow, _Mapping]] = ..., restore: _Optional[_Union[Restore, _Mapping]] = ..., factory_reset: _Optional[_Union[FactoryReset, _Mapping]] = ..., apply_update: _Optional[_Union[ApplyUpdate, _Mapping]] = ..., operation: _Optional[str] = ..., daemon: _Optional[str] = ..., json_args: _Optional[str] = ..., actor: _Optional[str] = ..., deadline_ms: _Optional[int] = ..., idempotency_key: _Optional[str] = ..., correlation_id: _Optional[str] = ..., required_confirmation: _Optional[str] = ...) -> None: ...

class TakeBackupNow(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Restore(_message.Message):
    __slots__ = ("backup_download_url",)
    BACKUP_DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    backup_download_url: str
    def __init__(self, backup_download_url: _Optional[str] = ...) -> None: ...

class FactoryReset(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ApplyUpdate(_message.Message):
    __slots__ = ("artifact_id", "artifact_download_url", "checksum_sha256")
    ARTIFACT_ID_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_DOWNLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    CHECKSUM_SHA256_FIELD_NUMBER: _ClassVar[int]
    artifact_id: str
    artifact_download_url: str
    checksum_sha256: str
    def __init__(self, artifact_id: _Optional[str] = ..., artifact_download_url: _Optional[str] = ..., checksum_sha256: _Optional[str] = ...) -> None: ...

class SignedUploadUrl(_message.Message):
    __slots__ = ("request_ref", "upload_url", "expires_at_unix_ms", "client_ref", "kind")
    REQUEST_REF_FIELD_NUMBER: _ClassVar[int]
    UPLOAD_URL_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    CLIENT_REF_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    request_ref: str
    upload_url: str
    expires_at_unix_ms: int
    client_ref: str
    kind: LogUploadRequest.Kind
    def __init__(self, request_ref: _Optional[str] = ..., upload_url: _Optional[str] = ..., expires_at_unix_ms: _Optional[int] = ..., client_ref: _Optional[str] = ..., kind: _Optional[_Union[LogUploadRequest.Kind, str]] = ...) -> None: ...
