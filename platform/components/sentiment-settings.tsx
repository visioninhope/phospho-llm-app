import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Form, FormField, FormItem, FormLabel } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { SentimentThreshold } from "@/models/models";
import { dataStateStore } from "@/store/store";
import { navigationStateStore } from "@/store/store";
import { zodResolver } from "@hookform/resolvers/zod";
import { useUser } from "@propelauth/nextjs/client";
import { set } from "date-fns";
import { Settings } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { useSWRConfig } from "swr";
import { z } from "zod";

export const SentimentSettings = ({}: {}) => {
  const [thresholdOpen, setThresholdOpen] = useState(false);
  const { mutate } = useSWRConfig();
  const dataFilters = navigationStateStore((state) => state.dataFilters);
  const tasksSorting = navigationStateStore((state) => state.tasksSorting);
  const tasksPagination = navigationStateStore(
    (state) => state.tasksPagination,
  );

  const { accessToken } = useUser();

  const selectedProject = dataStateStore((state) => state.selectedProject);
  const project_id = navigationStateStore((state) => state.project_id);

  const score = selectedProject?.settings?.sentiment_threshold?.score || 0.3;
  const magnitude =
    selectedProject?.settings?.sentiment_threshold?.magnitude || 0.6;

  const formSchema = z.object({
    score: z.number().min(0.05).max(1),
    magnitude: z.number().min(0.1).max(100),
  });

  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      score: score,
      magnitude: magnitude,
    },
  });

  function toggleButton() {
    setThresholdOpen(!thresholdOpen);
  }

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const { score, magnitude } = values;
    const threshold: SentimentThreshold = {
      score: score,
      magnitude: magnitude,
    };
    if (!selectedProject || !selectedProject.settings) {
      return;
    }
    selectedProject.settings.sentiment_threshold = threshold;

    const project_name = selectedProject.project_name;
    const settings = selectedProject.settings;
    fetch(`/api/projects/${project_id}`, {
      method: "POST",
      headers: {
        Authorization: "Bearer " + accessToken,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        project_name: project_name,
        settings: settings,
      }),
    }).then(() => {
      mutate(
        project_id
          ? [
              `/api/projects/${project_id}/tasks`,
              accessToken,
              tasksPagination.pageIndex,
              JSON.stringify(dataFilters),
              JSON.stringify(tasksSorting),
            ]
          : null,
      );
      toggleButton();
    });
  }

  if (!selectedProject) {
    return <></>;
  }

  return (
    <DropdownMenu open={thresholdOpen} onOpenChange={setThresholdOpen}>
      <DropdownMenuTrigger>
        <Button variant="ghost" size={"icon"} onClick={toggleButton}>
          <Settings size={18} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-full">
        <CardHeader>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
              <h2 className="text-lg font-bold">Sentiment threshold</h2>
              <FormField
                control={form.control}
                name="score"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="mr-2">
                      Score, Positive-Negative (0.05-1)
                    </FormLabel>
                    <Input
                      {...field}
                      type="number"
                      step="0.05"
                      className="input"
                      value={field.value}
                      onChange={(e) => {
                        field.onChange(e.target.valueAsNumber);
                      }}
                    />
                  </FormItem>
                )}
              ></FormField>
              <FormField
                control={form.control}
                name="magnitude"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel className="mr-2">
                      Magnitude, Neutral-Mixed (0.1-100)
                    </FormLabel>
                    <Input
                      {...field}
                      type="number"
                      step="0.1"
                      className="input"
                      value={field.value}
                      onChange={(e) => {
                        field.onChange(e.target.valueAsNumber);
                      }}
                    />
                  </FormItem>
                )}
              ></FormField>
              <div className="flex justify-center">
                <Button
                  type="submit"
                  variant="outline"
                  onClick={() => {
                    onSubmit(form.getValues());
                  }}
                >
                  Update
                </Button>
              </div>
            </form>
          </Form>
        </CardHeader>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
