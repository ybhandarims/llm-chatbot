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
environment: production
{{- end -}}

{{- define "chatapp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "chatapp.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "chatapp.securityContext" -}}
runAsNonRoot: true
runAsUser: 1000
fsReadOnlyRootFilesystem: false
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{- define "chatapp.containerSecurityContext" -}}
allowPrivilegeEscalation: false
capabilities:
  drop:
    - ALL
readOnlyRootFilesystem: false
{{- end -}}
