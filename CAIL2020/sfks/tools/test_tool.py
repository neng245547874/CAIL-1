import logging
import os
import torch
from torch.autograd import Variable
from timeit import default_timer as timer

from tools.eval_tool import gen_time_str, output_value

logger = logging.getLogger(__name__)



def test(parameters, config, gpu_list):
    # model = parameters["model"]
    if len(parameters) > 0:
        dataset = parameters[0]["test_dataset"]
    [p["model"].eval() for p in parameters]

    acc_result = None
    total_loss = 0
    cnt = 0
    total_len = len(dataset)
    start_time = timer()
    output_info = "testing"

    output_time = config.getint("output", "output_time")
    step = -1
    result = []

    for step, data in enumerate(dataset):
        # print(data)
        for key in data.keys():
            if isinstance(data[key], torch.Tensor):
                if len(gpu_list) > 0:
                    data[key] = Variable(data[key].cuda())
                else:
                    data[key] = Variable(data[key])
        if data['sorm'][0] == 1:
            results = parameters[1]["model"](data, config, gpu_list, acc_result, "test")
        else:
            results = parameters[0]["model"](data, config, gpu_list, acc_result, "test")
        # print(results)
        result = results["output"]
        cnt += 1

        if step % output_time == 0:
            delta_t = timer() - start_time

            output_value(0, "test", "%d/%d" % (step + 1, total_len), "%s/%s" % (
                gen_time_str(delta_t), gen_time_str(delta_t * (total_len - step - 1) / (step + 1))),
                         "%.3lf" % (total_loss / (step + 1)), output_info, '\r', config)

    if step == -1:
        logger.error("There is no data given to the model in this epoch, check your data.")
        raise NotImplementedError

    delta_t = timer() - start_time
    output_info = "testing"
    output_value(0, "test", "%d/%d" % (step + 1, total_len), "%s/%s" % (
        gen_time_str(delta_t), gen_time_str(delta_t * (total_len - step - 1) / (step + 1))),
                 "%.3lf" % (total_loss / (step + 1)), output_info, None, config)

    res = {}
    for x in result:
        res[x["id"]] = x["answer"]

    return res