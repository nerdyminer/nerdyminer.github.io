-- Aplica de forma consistente la identidad tipográfica de Kedro en prosa.
-- Los bloques y fragmentos de código quedan intactos por diseño.

function Str(element)
  local value = element.text
  local output = {}
  local cursor = 1
  local changed = false

  while true do
    local first, last = string.find(value, "Kedro", cursor, true)
    if not first then
      break
    end

    changed = true
    if first > cursor then
      table.insert(output, pandoc.Str(string.sub(value, cursor, first - 1)))
    end

    local token = "Kedro"
    if string.sub(value, first, first + 8) == "Kedro-Viz" then
      token = "Kedro-Viz"
      last = first + 8
    end

    table.insert(
      output,
      pandoc.Span({pandoc.Str(token)}, pandoc.Attr("", {"kedro-brand"}))
    )
    cursor = last + 1
  end

  if not changed then
    return nil
  end

  if cursor <= #value then
    table.insert(output, pandoc.Str(string.sub(value, cursor)))
  end
  return output
end
