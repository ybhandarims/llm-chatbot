{{- define "chatapp.name" -}}
chatapp
{{- end -}}

{{- define "chatapp.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "chatapp.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "chatapp.labels" -}}
app.kubernetes.io/name: {{ include "chatapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: Helm
{{- end -}}
