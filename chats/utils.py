import wave
import os


def join_wavs(samples, result_path):
    data= []
    params = None

    for sample in samples:
        file_field = sample.audio
        w = wave.open(file_field.path, 'rb')
        params = w.getparams()
        data.append(w.readframes(w.getnframes()))
        w.close()

    with wave.open(result_path, 'wb') as output:
        output.setparams(params)
        for row in data:
            output.writeframes(row)

    with open(result_path, 'rb') as f:
        res = f.read()
    
    os.remove(result_path)
    return res
