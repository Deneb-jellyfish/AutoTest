local key = KEYS[1]
local inputCode = ARGV[1]
local stored = redis.call('GET', key)
if not stored then
  return 0
end
if stored == inputCode then
  redis.call('DEL', key)
  return 1
end
return -1
